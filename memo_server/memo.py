from http import HTTPStatus
import random
import requests
import json
import urllib
import mysql.connector
import secrets

from flask import abort, Flask, make_response, render_template, Response, redirect, request

app = Flask(__name__)

#user_cookie 저장 dict
user_id_map = {}

naver_client_id = 'avXTBBSOccfdTzVTmLkb'
naver_client_secret = 'Zq4FSP1Od8'
naver_redirect_uri = 'http://mjubackend.duckdns.org:10218/auth'

# MySQL (쿼리문과 db는 처음 접해봐서 gpt의 도움을 받고 있습니다....)
def MySQLdb_connect():
    connection = mysql.connector.connect(
        host="127.0.0.1",       # MySQL 호스트
        port=50218,            # Docker에서 매핑한 포트
        user="root",           # MySQL 사용자
        password="root",       # MySQL 비밀번호
        database="memo_db",    # 데이터베이스 이름 (여기 확인 필요)
        charset="utf8mb4"      # 문자셋 설정
    )
    return connection

@app.route('/')
def home():
    # HTTP 세션 쿠키를 통해 이전에 로그인 한 적이 있는지를 확인한다.
    # 이 부분이 동작하기 위해서는 OAuth 에서 access token 을 얻어낸 뒤
    # user profile REST api 를 통해 유저 정보를 얻어낸 뒤 'userId' 라는 cookie 를 지정해야 된다.
    # (참고: 아래 onOAuthAuthorizationCodeRedirected() 마지막 부분 response.set_cookie('userId', user_id) 참고)
    userId = request.cookies.get('userId', default=None)
    name = None

    ####################################################
    # TODO: 아래 부분을 채워 넣으시오.
    #       userId 로부터 DB 에서 사용자 이름을 얻어오는 코드를 여기에 작성해야 함
    #로그인 쿠키가 있는 경우
    if userId in user_id_map:
        #db 연결 및 수정 부분 코드는 chat-gpt의 도움을 받아 작성하였습니다. 
        decryption_id=user_id_map[userId]
        db_connect=MySQLdb_connect()
        db_cursor=db_connect.cursor()
        
        db_cursor.execute('SELECT name FROM users WHERE id = %s', (decryption_id,))
        result = db_cursor.fetchone()
        if result:
            name = result[0]
        db_connect.commit()
        db_connect.close()
    ####################################################

    # 이제 클라에게 전송해 줄 index.html 을 생성한다.
    # template 로부터 받아와서 name 변수 값만 교체해준다.
    return render_template('index.html', name=name)


# 로그인 버튼을 누른 경우 이 API 를 호출한다.
# 브라우저가 호출할 URL 을 index.html 에 하드코딩하지 않고,
# 아래처럼 서버가 주는 URL 로 redirect 하는 것으로 처리한다.
# 이는 CORS (Cross-origin Resource Sharing) 처리에 도움이 되기도 한다.
#
# 주의! 아래 API 는 잘 동작하기 때문에 손대지 말 것
@app.route('/login')
def onLogin():
    params={
            'response_type': 'code',
            'client_id': naver_client_id,
            'redirect_uri': naver_redirect_uri,
            'state': random.randint(0, 10000)
        }
    urlencoded = urllib.parse.urlencode(params)
    url = f'https://nid.naver.com/oauth2.0/authorize?{urlencoded}'
    return redirect(url)


# 아래는 Authorization code 가 발급된 뒤 Redirect URI 를 통해 호출된다.
@app.route('/auth')
def onOAuthAuthorizationCodeRedirected():
    print("Request Args:", request.args)
    # TODO: 아래 1 ~ 4 를 채워 넣으시오.

    # 1. redirect uri 를 호출한 request 로부터 authorization code 와 state 정보를 얻어낸다.
    code = request.args.get('code')
    state = request.args.get('state')

    # 2. authorization code 로부터 access token 을 얻어내는 네이버 API 를 호출한다.
    token_url='https://nid.naver.com/oauth2.0/token'
    token_params={
        'grant_type': 'authorization_code',
        'client_id':naver_client_id,
        'redirect_uri': naver_redirect_uri,
        'client_secret': naver_client_secret,
        'code':code,
        'state':state
    }

    token_response = requests.post(token_url, params=token_params)
    token_response_data=token_response.json()
    access_token = token_response_data['access_token']
    refresh_token=token_response_data['refresh_token']
    # 3. 얻어낸 access token 을 이용해서 프로필 정보를 반환하는 API 를 호출하고,
    #    유저의 고유 식별 번호를 얻어낸다.
    profile_url='https://openapi.naver.com/v1/nid/me'
    profile_headers = {
    'Authorization': f'Bearer {access_token}' 
    }

    profile_response = requests.get(profile_url, headers=profile_headers)
    profile_response_data=profile_response.json()

    # 4. 얻어낸 user id 와 name 을 DB 에 저장한다.
    user_id = profile_response_data['response']['id'] 
    user_name=profile_response_data['response']['name'] 

    print(user_name + "이 로그인하였습니다.")

    #db 연결 및 수정 부분 코드는 chat-gpt의 도움을 받아 작성하였습니다. 
    db_connect=MySQLdb_connect()
    db_cursor=db_connect.cursor()
    #데이터를 넣고, 두번째 줄은 기본 키 업데이트 관련 정보 -> sql문 공부 필요
    db_cursor.execute('''
        INSERT INTO users (id, name) VALUES (%s, %s) 
        ON DUPLICATE KEY UPDATE name = VALUES(name)
    ''', (user_id, user_name)) #이상하게 한글이 깨짐 -> name : ???로 나옵니다... -> cnf 파일 추가로 해결
    db_connect.commit()
    db_connect.close()

    # 5. 첫 페이지로 redirect 하는데 로그인 쿠키를 설정하고 보내준다.
    #    user_id 쿠키는 "dkmoon" 처럼 정말 user id 를 바로 집어 넣는 것이 아니다.
    #    그렇게 바로 user id 를 보낼 경우 정보가 노출되기 때문이다.
    #    대신 user_id cookie map 을 두고, random string -> user_id 형태로 맵핑을 관리한다.
    #      예: user_id_map = {}
    #          key = random string 으로 얻어낸 a1f22bc347ba3 이런 문자열
    #          user_id_map[key] = real_user_id
    #          user_id = key

    #암호화 진행
    key = secrets.token_hex(16)
    user_id_map[key]=user_id

    response = redirect('/')
    response.set_cookie('userId', key)
    return response


@app.route('/memo', methods=['GET'])
def get_memos():
    # 로그인이 안되어 있다면 로그인 하도록 첫 페이지로 redirect 해준다.
    userId = request.cookies.get('userId', default=None)
    if not userId:
        return redirect('/')

    result = []

    # Decrypt userId
    if userId in user_id_map:
        decryption_id = user_id_map[userId]

        # DB 연결 및 메모 데이터 가져오기
        db_connect = MySQLdb_connect()
        db_cursor = db_connect.cursor()

        # 해당 유저의 메모 가져오기
        db_cursor.execute('SELECT memo FROM memos WHERE user_id = %s', (decryption_id,))
        all_memo = db_cursor.fetchall()

        # 메모 데이터를 result에 추가
        result.extend([{"text": memo[0]} for memo in all_memo])

        db_cursor.close()
        db_connect.close()

    # JSON 형식으로 메모 데이터 반환
    return {'memos': result}

@app.route('/memo', methods=['POST'])
def post_new_memo():
    # 로그인이 안되어 있다면 로그인 하도록 첫 페이지로 redirect 해준다.
    userId = request.cookies.get('userId', default=None)
    if not userId:
        return redirect('/')

    # 클라이언트로부터 JSON 을 받았어야 한다.
    if not request.is_json:
        abort(HTTPStatus.BAD_REQUEST)

    # TODO: 클라이언트로부터 받은 JSON 에서 메모 내용을 추출한 후 DB에 userId 의 메모로 추가한다.
    request_data=request.get_json()
    request_memo=request_data.get('text', None)

    print(request_memo + "과 같은 내용을 저장하겠습니다.")

    decryption_id=user_id_map[userId]
    db_connect=MySQLdb_connect()
    db_cursor=db_connect.cursor()

    # SQL문은 gpt의 도움을 받았습니다
    db_cursor.execute('INSERT INTO memos (user_id, memo) VALUES (%s, %s)', (decryption_id, request_memo))
    db_connect.commit()

    db_cursor.close()
    db_connect.close()
    #
    return '', HTTPStatus.OK


if __name__ == '__main__':
    app.run('0.0.0.0', port=8000, debug=True)