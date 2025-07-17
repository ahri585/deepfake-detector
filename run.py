from myapp import create_app
from flask_cors import CORS

app= create_app()

# 모든 출처에서 오는 요청을 허용
CORS(app)
#CORS(app, origins=["도메인주소"])로 특정도메인만 접속하도록 설정 가능

# 모든 IP에서 5000번 포트로 접속 가능
if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5000)
