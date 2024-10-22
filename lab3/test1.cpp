#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>

#include <iostream>

using namespace std;

int main(){
    int s=socket(AF_INET, SOCK_DGRAM,IPPROTO_UDP);

    cout<< "Socekt ID: "<<s<<endl;

    close(s);
    return 0;
}
