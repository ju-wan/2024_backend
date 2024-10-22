#include <arpa/inet.h>
#include <errno.h>
#include <string.h>
#include <sys/socket.h>

#include <unistd.h>
#include <iostream>

using namespace std;

int main(){
    int passiveSock=socket(AF_INET, SOCK_STREAM,IPPROTO_TCP);

    struct sockaddr_in sin; //sin 초기화하고 bind까지 설정 
    memset(&sin, 0, sizeof(sin));
    sin.sin_family=AF_INET;
    sin.sin_addr.s_addr=INADDR_ANY;
    sin.sin_port=htons(10218);
    if(bind(passiveSock,(struct sockaddr *)&sin,sizeof(sin))<0){
        cerr<<"bind() failed"<<strerror(errno)<<endl;
        return 1;
    }

    if(listen(passiveSock,10)<0){ //설정한 소켓 listen
        cerr<<"listen() failed: "<<strerror(errno)<<endl;
        return 1;
    }

    //connect 시도 

    memset(&sin,0,sizeof(sin)); //시도한 연결 accpet 근데 sin은 왜 0으로 최기화하는거지? -> gpt 답변 : accept() 함수의 역할: accept()가 호출되면, 클라이언트가 연결되었을 때 해당 클라이언트의 IP 주소와 포트 정보가 sin에 자동으로 채워짐. 즉, 초기화로 기존 정보가 사라져도 accept()에서 새로운 값이 들어오기 때문에 문제가 되지 않아. 내가 수업에서 이 내용을 놓쳤을지도
    unsigned int sin_len=sizeof(sin);
    int clientSock=accept(passiveSock,(struct sockaddr *) &sin,&sin_len);
    if(clientSock<0){
        cerr<<"accept() failed: "<<strerror(errno)<<endl;
        return 1;
    }

    char buf[65536]; //정보 받기
    int numRecv = recv(clientSock, buf, sizeof(buf),0);
    if(numRecv==0){
        cout<<"Socket closed:"<<clientSock<<endl;
    }
    else if(numRecv<0){
        cerr<<"recv() failed: "<<strerror(errno)<<endl;
    }
    else{
        cout<<"Received: "<<numRecv<<"bytes, clientSock"<<clientSock<<endl;
    }

    int offset=0; //다시 정보 보내기 tcp이기 때문에 갈때까지 while문을 통해서 보냄
    while(offset<numRecv){
        int numSend=send(clientSock,buf+offset,numRecv-offset,0);
        if(numSend<0){
            cerr<<"send() failed: "<<strerror(errno)<<endl;
        }
        else{
            cout<<"Sent: "<<numSend<<endl;
            offset+=numSend;
        }
    }

    close(clientSock);
    close(passiveSock);
}