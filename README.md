# 🧠 Deepfake Detector (Flask + Gunicorn + Nginx)

이 프로젝트는 이미지 기반 딥페이크 탐지 웹서비스입니다.  
Flask를 기반으로 API 서버를 구성하고, Gunicorn + Nginx로 배포합니다.

---

## 📦 프로젝트 구성

- `Flask` 웹 서버
- `EfficientNet-B3` 기반 딥러닝 모델
- `Gunicorn` WSGI 서버
- `Nginx` 리버스 프록시
- AWS EC2 (Ubuntu)

---

## ⚙️ 서버 설정 및 실행 방법

### 1. 가상환경 생성 및 의존성 설치
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

2. 개발용 서버 실행 (수정 자동 반영)
nohup gunicorn --reload -w 2 -b 0.0.0.0:5000 run:app > log.txt 2>&1 &

3. 운영용 서비스 등록 (systemd + Gunicorn)
📄 deploy/gunicorn.service

[Unit]
Description=Gunicorn instance to serve Flask app
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/deepfake-detector
ExecStart=/home/ubuntu/deepfake-detector/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 run:app

[Install]
WantedBy=multi-user.target

⏩ 등록 및 실행
sudo cp deploy/gunicorn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn

4. Nginx 설정 (80포트 → 5000 포트 프록시)
📄 deploy/nginx.conf

server {
    listen 80;
    server_name YOUR.DOMAIN.or.IP;

    location / {
        proxy_pass http://127.0.0.1:5000;
        include proxy_params;
        proxy_redirect off;
    }
}

⏩ 활성화
sudo cp deploy/nginx.conf /etc/nginx/sites-available/deepfake
sudo ln -s /etc/nginx/sites-available/deepfake /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl reload nginx

📁 기타 참고
.gitignore에 instance/database.db, .env, __pycache__/ 등이 포함되어야 함.

모델 파일 .pth는 로컬 업로드 필요 (현재 경로: test/models/)

React 등 프론트엔드 연동은 추후 확장 예정

🙋‍♀️ 만든 사람


💻 서버: Flask, AWS EC2

🧠 모델: EfficientNet-B3 finetuned
