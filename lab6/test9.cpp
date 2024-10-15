#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
#include <mutex>

using namespace std;

int sum=0;
mutex m;
mutex m2;

void f(){
    for(int i=0;i<10*1000*1000;++i){
        m.lock();
        m2.lock();
        ++sum;
        m.unlock();
        m2.unlock();
    }
}

int main(){
    thread t(f);
    for(int i=0;i<10*1000*1000;++i){
        m2.lock();
        m.lock();
        ++sum;
        m2.unlock();
        m.unlock();
    }
    t.join();
    cout<<"Sum: "<<sum<<endl;
}

//계속해서 순환대기가 이루어지고 있음. m2->m 순서로 lock을 걸었으면, unlock 순서는 m->m2가 돼야만 함.