실습 서버 버전 memo_server 구현
해당 위치에서 

flask --app memo run --port 10218 --host 0.0.0.0

를 사용하시면 됩니다.

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
