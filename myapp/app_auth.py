from flask import Blueprint, request, jsonify, current_app
from .models import User, db
import jwt
import datetime
from werkzeug.security import generate_password_hash
from functools import wraps

app_auth_bp = Blueprint('app_auth', __name__, url_prefix='/api')

@app_auth_bp.route('/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')

    if isinstance(token, bytes):
        token = token.decode('utf-8')

    return jsonify({'success': True, 'message': 'Login successful', 'token': token}), 200


@app_auth_bp.route('/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password or not email:
        return jsonify({'success': False, 'message': 'Username, password and email required'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Username already exists'}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password, email=email)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'success': True, 'message': 'User created successfully'}), 201


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split()[1]
        if not token:
            return jsonify({'success': False, 'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'message': 'Invalid token!'}), 401

        return f(current_user_id=current_user_id, *args, **kwargs)

    return decorated
@app_auth_bp.route('/change_password', methods=['POST'])
@token_required
def change_password(current_user_id):
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not current_password or not new_password or not confirm_password:
        return jsonify({'success': False, 'message': '모든 비밀번호 필드를 입력해주세요'}), 400

    if new_password != confirm_password:
        return jsonify({'success': False, 'message': '새 비밀번호가 일치하지 않습니다'}), 400

    user = User.query.get(current_user_id)

    if not user or not user.check_password(current_password):
        return jsonify({'success': False, 'message': '현재 비밀번호가 올바르지 않습니다'}), 401

    user.password = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({'success': True, 'message': '비밀번호가 성공적으로 변경되었습니다'}), 200
