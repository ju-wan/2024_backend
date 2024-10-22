#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <string.h>
#include <unistd.h>

#include <iostream>
#include <string>

using namespace std;

int main(){
    int s= socket(AF_INET, SOCK_DGRAM,IPPROTO_UDP); //소켓 설정
    if(s<0) return 1;

    struct sockaddr_in sin; //sin 정보 초기화
    sin.sin_family=AF_INET;
    sin.sin_addr.s_addr=INADDR_ANY;
    sin.sin_port=htons(10000+218);

    if(bind(s,(struct sockaddr *)&sin, sizeof(sin))<0){ //소켓과 sin을 bind
        cerr<<strerror(errno)<<endl;
        return 0;
    } 

    while(true){
        char buf[65536];
        struct sockaddr_in cli_sin;
        __socklen_t sin_size = sizeof(cli_sin);

        ssize_t recv_bytes=recvfrom(s,buf,sizeof(buf),0,(struct sockaddr *) &cli_sin, &sin_size);
        if(recv_bytes==-1){ //정보 받기
            cerr<<strerror(errno)<<endl;
            return 0;
        }
        buf[recv_bytes] = '\0';

        if(sendto(s,buf,recv_bytes,0,(struct sockaddr *) &cli_sin,sin_size)==-1){ //정보 보내기
            cerr<<strerror(errno)<<endl;
            return 0;
        }
    }

    close(s);
    return 0;
}