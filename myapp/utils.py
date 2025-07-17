# utils.py
from PIL import Image as PILImage
from functools import wraps
from flask import request, jsonify, current_app
import jwt, datetime
from flask import make_response
import imghdr
import logging 
from PIL import Image

logger = logging.getLogger(__name__)
# 파일 확장자 체크 함수
def allowed_file(filename):
    allowed_extensions = {"png", "jpg", "jpeg", "gif"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

# 이미지 리사이징 함수
def resize_image(filepath, size=(200, 200)):
    try:
        img = PILImage.open(filepath)
        img = img.resize(size)

        # RGBA → RGB 변환 (투명도 제거)
        if img.mode == "RGBA":
            img = img.convert("RGB")

        img.save(filepath)
        print(f"✅ 이미지 리사이징 완료: {filepath}")

    except Exception as e:
        print(f"❌ 이미지 리사이징 실패: {e}")


# 캐시 방지 헤더 데코레이터(로그인한 사용자만 볼수 있는 페이지에서 응답에 캐시 방지
# 헤더를 넣어 브라우저가 페이지를 저장할 수 없게 함
def nocache(view):
    @wraps(view)
    def no_cache_wrapper(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return no_cache_wrapper

#토큰 인증 데코레이터
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Authorization 헤더에서 토큰 추출
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        try:
            secret_key = current_app.config["SECRET_KEY"]
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            user_id = payload["user_id"]  # JWT payload 안에 user_id가 있어야 함
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 401

        return f(user_id=user_id, *args, **kwargs)

    return decorated

# 토큰 생성 함수
def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # 1시간 유효
    }
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
    return token



def is_valid_image(file):
    try:
        file.seek(0)
        header_type = imghdr.what(file)
        logger.debug(f"[DEBUG] imghdr.what = {header_type}")


        if header_type not in ["jpeg","png"]:
            logger.debug("허용되지 않는 이미지 타입입니다")
            return False

        file.seek(0)
        Image.open(file).verify()
        file.seek(0)
        logger.debug("PIL 이미지 검증 통과")
        return True
    except Exception as e:
        logger.exception(f"이미지 유효성 검사 중 오류 발생: {e}")
        return False
