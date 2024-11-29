실습 서버 버전 memo_server 구현 ------------------------------------------------------------------------
해당 위치에서 

flask --app memo run --port 10218 --host 0.0.0.0

를 사용하시면 됩니다.

http://mjubackend.duckdns.org:10218

으로 접속하시면 됩니다.

현제 상태는 docker가 꺼져있습니다.

해당 command를 사용하여 docker을 run하시면 됩니다.

docker start mysql-jawan

+추가적으로 run command는 다음과 같습니다. (해당 이름의 container 삭제되었을 경우에만 사용)

docker run --name mysql-jawan \
    -e MYSQL_ROOT_PASSWORD=root \
    -e MYSQL_DATABASE=memo_db \
    -p 50218:3306 \
    -v $(pwd)/my.cnf:/etc/mysql/my.cnf \
    --restart unless-stopped \
    -d mysql:latest

-v $(pwd)/my.cnf:/etc/mysql/my.cnf \ 는 opensql 환경에서도 한글이 깨지지 않기 위한 설정파일입니다.

mysql 정보를 확인히시기 위하여
sudo docker exec -it mysql-jawan mysql -u root -p
USE memo_db;
로 확인하시면 되고, 비밀번호는 root 입니다.

aws 버전 memo_server 구현 ------------------------------------------------------------------------
자세한 정보는 해당 경로에 보고서를 참고 부탁드립니다.

사용한 docker은 실습 서버의 docker와 같고, 비밀번호는 root 입니다.
부여된 dns는

http://melba-1292013705.ap-northeast-2.elb.amazonaws.com/memo

와 같습니다. 이를 통하여 접속해 주시면 감사드리겠습니다.


