import errno
import json
import select
import socket
import sys
import threading

from queue import Queue
from absl import app, flags

FLAGS = flags.FLAGS

import message_pb2 as pb

flags.DEFINE_integer(name='port', default=None, required=True, help='서버 port 번호')
flags.DEFINE_enum(name='format', default='json', enum_values=['json', 'protobuf'], help='메시지 포맷')

message_queue = Queue()
mutex=threading.Lock()
cv= threading.Condition(mutex)
shutdown_flag = threading.Event()

room_count=1
rooms={}
client_names = {}
client_rooms = {}
client_threads = []

#equal with client.py code
def send_messages_to_client(sock, messages):
  '''
  TCP socket 상으로 message 를 전송한다.
  앞에 길이에 해당하는 2 byte 를 network byte order 로 전송한다.

  :param sock: 서버와 맺은 TCP socket
  :param messages: 전송할 message list.각 메시지는 dict type 이거나 protobuf type 이어야 한다.
  '''
  assert isinstance(messages, list)

  if sock.fileno() == -1:
        raise RuntimeError("소켓이 닫혀 있습니다.")
  
  for msg in messages:
    msg_str = None
    if FLAGS.format == 'json':
      serialized = bytes(json.dumps(msg), encoding='utf-8')
      msg_str = json.dumps(msg)
    else:
      serialized = msg.SerializeToString()
      msg_str = str(msg).strip()

    to_send = len(serialized)
    to_send_big_endian = int.to_bytes(to_send, byteorder='big', length=2)
 
    serialized = to_send_big_endian + serialized

    offset = 0
    attempt = 0
    while offset < len(serialized):
      num_sent = sock.send(serialized[offset:])
      if num_sent <= 0:
        raise RuntimeError('Send failed')
      offset += num_sent

#for sending SCSystemMessage to client
def send_SCSystemMessage_to_client(cli_sock,str):
    messages = []
    
    if FLAGS.format == 'json':
        cli_msg = {"type": "SCSystemMessage", "text": str}
        messages.append(cli_msg)
    else:
        cli_msg = pb.Type()
        cli_msg.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE
        messages.append(cli_msg)

        cli_msg = pb.SCSystemMessage()
        cli_msg.text = str
        messages.append(cli_msg)

    send_messages_to_client(cli_sock,messages)
    
#for CSName
def change_name(message,cli_sock):
    if FLAGS.format == 'json':
        name = message.get("name")
    elif FLAGS.format == 'protobuf':
        name = message.name
    
    if name:
        client_names[cli_sock] = name
        send_SCSystemMessage_to_client(cli_sock,f"이름이 {name}으로 변경되었습니다.")
    else:
        send_SCSystemMessage_to_client(cli_sock,f"유효하지 않은 이름입니다.")
        print("유효하지 않은 이름입니다.")

#for CSRooms
def checking_roomlists(message,cli_sock):
    messages = []
    if not rooms:
        send_SCSystemMessage_to_client(cli_sock,"생성된 방이 없습니다.")
    else:
        rooms_list = []

        # match for client(json)
        if FLAGS.format == 'json':
            for room_id, room_info in rooms.items():
                room_data = {
                    "roomId": room_id,
                    "title": room_info["title"],
                    "members": [client_names[sock] for sock in room_info["members"]]
                }
                rooms_list.append(room_data)

            cli_msg = {
                "type": "SCRoomsResult",
                "rooms": rooms_list
            }

            messages.append(cli_msg)
        # match for client(protobuf)
        else:
            # Type 메시지 작성 (SCRoomsResult 타입 지정)
            type_message = pb.Type()
            type_message.type = pb.Type.MessageType.SC_ROOMS_RESULT
            messages.append(type_message)

            # SCRoomsResult 메시지 작성
            rooms_result_msg = pb.SCRoomsResult()
            for room_id, room_info in rooms.items():
                room = rooms_result_msg.rooms.add()
                room.roomId = room_id
                room.title = room_info["title"]

                for client in [client_names[sock] for sock in room_info["members"]]:
                    if isinstance(client, tuple):
                        member_str = f"({client[0]}, {client[1]})"  # 튜플 형식을 문자열로 변환
                    else:
                        member_str = client  # 문자열 그대로 사용
                room.members.append(member_str)  # 개별 멤버 추가

            # `SCRoomsResult` 메시지를 `messages` 리스트에 추가
            messages.append(rooms_result_msg)
        send_messages_to_client(cli_sock, messages)

#for CSCreateRoom
def create_room(message,cli_sock):
    global room_count
    messages = []
    if FLAGS.format == 'json':
        title = message.get("title")
    elif FLAGS.format == 'protobuf':
        title = message.title

    if title:
        # if there are alreay room
        if cli_sock in client_rooms:
            send_SCSystemMessage_to_client(cli_sock,"대화 방에 있을 때는 방을 개설 할 수 없습니다.")
            return
        
        # if there are same name room
        elif any(room_info["title"] == title for room_info in rooms.values()):
            send_SCSystemMessage_to_client(cli_sock,"같은 이름의 채팅방이 이미 존재합니다.")
            return
        
        # create new room
        room_id = room_count
        rooms[room_id] = {"title": title, "members": [cli_sock]}
        client_rooms[cli_sock] = room_id
        room_count += 1  

        send_SCSystemMessage_to_client(cli_sock,f"방제[{title}] 방에 입장했습니다.")
    else:
        send_SCSystemMessage_to_client(cli_sock,"유효하지 않은 방 제목입니다.")
        print("유효하지 않은 방 제목이 전달되었습니다.")

#for CSJoinRoom
def join_room(message,cli_sock):
    if FLAGS.format == 'json':
        room_id = message.get("roomId")
    elif FLAGS.format == 'protobuf':
        room_id = message.roomId
    messages = []

    # if there are alreay room
    if cli_sock in client_rooms:
        send_SCSystemMessage_to_client(cli_sock,"대화 방에 있을 때는 다른 방에 들어갈 수 없습니다.")
        return
    
    #if there are not room num
    if room_id not in rooms:
        send_SCSystemMessage_to_client(cli_sock,"대화방이 존재하지 않습니다.")
        return

    #get in room
    rooms[room_id]["members"].append(cli_sock)
    client_rooms[cli_sock] = room_id

    #send message to user
    send_SCSystemMessage_to_client(cli_sock,f"방제[{rooms[room_id]['title']}] 방에 입장했습니다.")

    #send message to other user
    for sock in rooms[room_id]["members"]:
        if(sock!=cli_sock): #if not me
            send_SCSystemMessage_to_client(sock,f"[{client_names[cli_sock]}] 님이 입장했습니다.")

#for CsLeaveRoom
def leave_room(message,cli_sock):
    # if there are not room
    if cli_sock not in client_rooms:
        send_SCSystemMessage_to_client(cli_sock,"현재 대화방에 들어가 있지 않습니다.")
        return
    
    #save tmp data
    room_id=client_rooms[cli_sock]
    room_title=rooms[room_id]["title"]

    #delete data
    del client_rooms[cli_sock] 
    rooms[room_id]["members"].remove(cli_sock)

    #send message to user
    send_SCSystemMessage_to_client(cli_sock,f"방제[{room_title}] 방에서 퇴장했습니다.")

    #send message to other user
    for sock in rooms[room_id]["members"]:
            send_SCSystemMessage_to_client(sock,f"[{client_names[cli_sock]}]님이 퇴장했습니다.")

def handle_shutdown_command(message,cli_sock):
    shutdown_flag.set()

#for CSShutdown
def shutdown_server(sock_list, server_sock):
    print("서버를 종료 중입니다...")
    
    # 모든 클라이언트 소켓 닫기
    for sock in sock_list:
        if sock != server_sock:
            try:
                send_SCSystemMessage_to_client(sock, "서버가 종료됩니다.")
                sock.close()
            except Exception as e:
                print(f"소켓 닫기 중 오류: {e}")

    # 워커 스레드 종료 신호
    for _ in client_threads:
        with cv:
            message_queue.put(None)
            cv.notify_all()

    # 모든 워커 스레드가 종료될 때까지 대기
    for thread in client_threads:
        thread.join()

    server_sock.close()
    print("서버 종료 완료.")
    sys.exit(0)

#for CSChat
def chat(message,cli_sock):
    messages=[]
    # if there are not room
    if cli_sock not in client_rooms:
        send_SCSystemMessage_to_client(cli_sock,"현재 대화방에 들어가 있지 않습니다.")
        return
    
    room_id=client_rooms[cli_sock]
    if FLAGS.format == 'json':
        cli_msg={
            "type": "SCChat",
            "member":client_names[cli_sock],
            "text":message.get("text")
        }

        messages.append(cli_msg)
    else:
        type_message=pb.Type()
        type_message.type=pb.Type.MessageType.SC_CHAT
        messages.append(type_message)

        cli_msg=pb.SCChat()
        if isinstance(client_names[cli_sock], tuple):
            cli_msg.member = f"({client_names[cli_sock][0]}, {client_names[cli_sock][1]})"  # 튜플을 문자열로 변환하여 할당
        else:
            cli_msg.member = client_names[cli_sock]  # 문자열인 경우 그대로 할당
        cli_msg.text=message.text

        messages.append(cli_msg)

    for sock in rooms[room_id]["members"]:
        send_messages_to_client(sock, messages)

#Message Handler by ppt No.12
msg_map = {
    # for json
    "CSName": change_name,
    "CSRooms": checking_roomlists,
    "CSCreateRoom": create_room,
    "CSJoinRoom": join_room,
    "CSLeaveRoom": leave_room,
    "CSShutdown": handle_shutdown_command,
    "CSChat": chat,

    # for protobuf
    pb.Type.CS_NAME: change_name,
    pb.Type.CS_ROOMS: checking_roomlists,
    pb.Type.CS_CREATE_ROOM: create_room,
    pb.Type.CS_JOIN_ROOM: join_room,
    pb.Type.CS_LEAVE_ROOM: leave_room,
    pb.Type.CS_SHUTDOWN: handle_shutdown_command,
    pb.Type.CS_CHAT: chat
}

msg_proto_parsers = {
    pb.Type.MessageType.CS_NAME: pb.CSName.FromString,
    pb.Type.MessageType.CS_ROOMS: pb.CSRooms.FromString,
    pb.Type.MessageType.CS_CREATE_ROOM: pb.CSCreateRoom.FromString,
    pb.Type.MessageType.CS_JOIN_ROOM: pb.CSJoinRoom.FromString,
    pb.Type.MessageType.CS_LEAVE_ROOM: pb.CSLeaveRoom.FromString,
    pb.Type.MessageType.CS_SHUTDOWN: pb.CSShutdown.FromString,
    pb.Type.MessageType.CS_CHAT: pb.CSChat.FromString
}

# bind -> listen
def connect_with_client(port):
    # make socket
    passive_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    passive_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # listen
    passive_sock.bind(('0.0.0.0', port))
    passive_sock.listen(10)

    print(f"Server is listening on port {port}...")

    # return server socket (passive_sock)
    return passive_sock


#worker
def cousume_work(num):
    print(f"메시지 작업 쓰레드 #{num} 생성")
    while True:
        # message_queue가 공유자원 -> mutex
        with cv:
            while message_queue.empty():
                cv.wait()
            # 종료 신호 감지
            task = message_queue.get()
            if task is None:  # 종료 신호 확인
                print(f"메시지 작업 쓰레드 #{num} 종료")
                message_queue.task_done()
                break  # 루프 종료하여 쓰레드 종료

        # 일반적인 작업 처리
        message, sock, type_message = task

        if sock and message:
            msg_map[type_message](message, sock)

        message_queue.task_done()

#produecer
def produce_work(message, sock,type_message):
    #message_queue가 공유자원 -> mutex
    with cv:
        message_queue.put((message, sock,type_message))
        cv.notify()

#교수님의 조언...
class ClientHandler:
    def __init__(self, sock):
        self.sock = sock
        self.current_message_len = None
        self.socket_buffer = b""
        self.current_protobuf_type = None

    def recv_the_data(self):
        '''
        소켓으로부터의 입력을 처리한다.
        '''
        received_buffer = self.sock.recv(65535)
        if not received_buffer:
            return False

        self.socket_buffer += received_buffer

        # 여태까지 읽은 데이터가 여러 메시지를 포함하고 있을 수 있다.
        # 메시지를 디코딩 할 수 있는 한 계속 반복한다.
        while True:
            # 아직 읽어야될 길이 정보를 모른다면 이번 라운드는 스킵한다.
            if self.current_message_len is None:
                if len(self.socket_buffer) < 2:
                    return True  # 아직 데이터가 부족하다

                # 읽어야 될 길이를 확인했다.
                self.current_message_len = int.from_bytes(self.socket_buffer[:2], byteorder='big')
                self.socket_buffer = self.socket_buffer[2:]

            # 현재 가지고 있는 데이터가 메시지를 decoding 하기에 충분하지 않다면 다음을 기약한다.
            if len(self.socket_buffer) < self.current_message_len:
                return True

            # 처리할 메시지 길이만큼을 잘라낸다.
            serialized = self.socket_buffer[:self.current_message_len]
            self.socket_buffer = self.socket_buffer[self.current_message_len:]
            self.current_message_len = None

            # JSON 은 그 자체로 바로 처리 가능하다.
            if FLAGS.format == 'json':
                msg = json.loads(serialized)
                type_message = msg.get('type', None)

                if type_message not in msg_map:
                    print(f"Invalid type: {type_message}")
                else:
                    produce_work(msg, self.sock, type_message)
            else:
                # 현재 type 을 모르는 상태다. 먼저 TypeMessage 를 복구한다.
                if self.current_protobuf_type is None:
                    msg = pb.Type.FromString(serialized)

                    if msg.type in msg_proto_parsers and msg.type in msg_map:
                        self.current_protobuf_type = msg.type
                    else:
                        print(f"Invalid type: {msg.type}")
                else:
                    # type 을 알고 있으므로 parser 를 이용해서 메시지를 복구한다.
                    msg = msg_proto_parsers[self.current_protobuf_type](serialized)
                    # type 에 따른 message handler 를 찾아서 호출한다.
                    try:
                        produce_work(msg, self.sock, self.current_protobuf_type)
                    finally:
                        # 다음에 type 부터 decoding 하게끔 초기화 한다.
                        self.current_protobuf_type = None
        return True

def init_worker(num):
    for i in range(num):
        thread = threading.Thread(target=cousume_work, args=(i,), daemon=True)
        thread.start()
        client_threads.append(thread)


def main(argv):
    if not FLAGS.port:
        print('서버의 Port 번호를 지정해야 됩니다.')
        sys.exit(2)
    
    # first socket connect
    server_sock = connect_with_client(FLAGS.port)
    sock_list = [server_sock]

    client_handlers = {}

    #can fix worker
    init_worker(2)

    try:
        # can connect with many clients by using select
        while True:
            if shutdown_flag.is_set():
                shutdown_server(sock_list, server_sock)
            read_sock, _, exception_sock = select.select(sock_list, [], sock_list,1.0)

            for tmp_sock in read_sock:
                # if server socket, accept new connection
                if tmp_sock == server_sock:
                    client_sock, client_address = tmp_sock.accept()
                    client_names[client_sock]=client_address
                    print(f"새로운 클라이언트 접속 {client_names[client_sock]}")
                    sock_list.append(client_sock)

                    client_handlers[client_sock] = ClientHandler(client_sock)
                else:
                    if not client_handlers[tmp_sock].recv_the_data():
                        # 연결 종료 처리
                        print(f"클라이언트 연결 종료: {client_names[tmp_sock]}")
                        sock_list.remove(tmp_sock)
                        del client_names[tmp_sock]
                        del client_handlers[tmp_sock]
    except KeyboardInterrupt:
        print("\n서버 종료 신호를 받았습니다.")
        shutdown_server(sock_list, server_sock)
        sys.exit(0)  # 프로그램 완전 종료
        
if __name__ == '__main__':
  app.run(main)