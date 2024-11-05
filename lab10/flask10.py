#!/usr/bin/python3

from flask import Flask
from flask import make_response
from flask import request

app = Flask(__name__)

@app.route('/<arg1>/<op>/<arg2>', methods=['GET'])
def calc_get(arg1,op,arg2):
    try:
        arg1=float(arg1)
        arg2=float(arg2)
        
        if(op=='+'):
            ans=arg1+arg2
        elif(op=='-'):
            ans=arg1-arg2
        elif(op=='*'):
            ans=arg1*arg2
        else:
            return make_response("연산자가 틀립니다.",400)
        return make_response(f"결과는 {ans}",200)
    except ValueError:
            return make_response("처리할 수 없는 숫자 포맷입니다.",400)
    except Exception as e:
        return make_response(f"기타 예외: {str(e)}", 400)
    
@app.route('/', methods=['POST'])
def calc_post():
    try:
        data = request.get_json()
        arg1 = data.get('arg1', '')
        op = data.get('op', '')
        arg2 = data.get('arg2', '')

        arg1=float(arg1)
        arg2=float(arg2)

        if(op=='+'):
            ans=arg1+arg2
        elif(op=='-'):
            ans=arg1-arg2
        elif(op=='*'):
            ans=arg1*arg2
        else:
            return make_response("연산자가 틀립니다.",400)
        return make_response(f"결과는 {ans}",200)
    except ValueError:
            return make_response("처리할 수 없는 숫자 포맷입니다.",400)
    except Exception as e:
        return make_response(f"기타 예외: {str(e)}", 400)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10218)