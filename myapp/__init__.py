import os
import logging
from datetime import datetime

from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS

from .auth import auth_bp
from .app_auth import app_auth_bp
from .models import db, User, Image  # noqa: F401 (Image가 다른 곳에서 쓰이면 유지)

# ===== 로깅 디렉토리 준비 =====
log_dir = "/home/ubuntu/deepfake-detector/logs"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "server.log")),
        logging.StreamHandler(),
    ],
)

# 전역 확장 인스턴스
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # ---- 블루프린트 임포트(순환참조 방지 위치) ----
    from .routes import main_bp, web_bp

    # ---- 기본 설정 ----
    app.config["DEBUG"] = True
    app.config["TESTING"] = False

    app.config["SECRET_KEY"] = "9012b12f50045abb3551a3e40e2f125eeb198a41d815bd2f"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
    app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg"}

    # ---- DB/마이그레이트 ----
    db.init_app(app)
    migrate.init_app(app, db)

    # ---- CORS (필요시 도메인 갱신) ----
    CORS(
        app,
        supports_credentials=True,
        resources={
            r"/api/*": {
                "origins": "https://bc34-2406-5900-5072-c1-e099-8074-66e6-4e68.ngrok-free.app"
            }
        },
    )

    # ---- Flask-Login ----
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ---- Jinja 컨텍스트 주입: current_year ----
    @app.context_processor
    def inject_current_year():
        # 서버 표준은 UTC. KST가 필요하면 zoneinfo로 변환 가능.
        return {"current_year": datetime.utcnow().year}

    # ---- 블루프린트 등록 ----
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(app_auth_bp)
    app.register_blueprint(web_bp)

    return app

