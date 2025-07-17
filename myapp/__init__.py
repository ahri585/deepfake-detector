import os
from flask import Flask
from flask_migrate import Migrate
from .auth import auth_bp
from .routes import main_bp, web_bp
from .models import db, User
from flask_login import LoginManager
from .app_auth import app_auth_bp
from flask_cors import CORS
import logging
logging.basicConfig(level=logging.INFO)

# Flask-Login 매니저 전역 생성
login_manager = LoginManager()

# Flask-Migrate 인스턴스 생성
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    app.config['DEBUG'] = True
    app.config['TESTING'] = False

    app.config["SECRET_KEY"] = "9012b12f50045abb3551a3e40e2f125eeb198a41d815bd2f"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")

    app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg"}

    # DB 초기화
    db.init_app(app)
    migrate.init_app(app, db)

    # Blueprint 등록
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(app_auth_bp)
    app.register_blueprint(web_bp)

    #CORS 설정
    CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "https://bc34-2406-5900-5072-c1-e099-8074-66e6-4e68.ngrok-free.app"}})

    # 로그인 매니저 초기화
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # 로그인 필요시 리다이렉트할 뷰 이름

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app




