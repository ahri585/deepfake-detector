from flask import Blueprint, request, Response, send_from_directory, render_template, url_for, session,jsonify,current_app
from werkzeug.utils import secure_filename
from .utils import allowed_file, resize_image, nocache, is_valid_image
from .models import Image, db
from myapp.ai import detect_and_classify
from .models import Image as ImageModel
import os,uuid,json,jwt
from flask_cors import CORS
from flask_login import login_required, current_user
from .app_auth import token_required

main_bp = Blueprint('main', __name__, url_prefix='/api')
CORS(main_bp)

web_bp = Blueprint('web',__name__)
CORS(web_bp)

upload_folder = '/home/ubuntu/deepfake-detector/myapp/static/uploads'

if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

@main_bp.route('/api/upload', methods=['POST'])
@token_required
def upload_app(current_user_id):  # <- token_required 데코레이터가 user_id를 추출해 전달
    text_data = request.form.get("text", "")
    user_id = current_user_id

    if "image" in request.files:
        file = request.files["image"]

        if file.filename == "":
            return Response(json.dumps({"error": "선택된 파일이 없습니다."}, ensure_ascii=False), mimetype='application/json'), 400

        original_filename = file.filename
        if '.' not in original_filename:
            original_filename +=".jpg"
        original_filename = secure_filename(original_filename)
        unique_fielname = f"{uuid.uuid4().hex}_{original_filename}"
        filepath = os.path.join(upload_folder, unique_filename)

        if is_valid_image(file):
            try:
                file.save(filepath)
                resize_image(filepath)
                result_label, score, _ = detect_and_classify(filepath)

                if result_label == "NoFace":
                    result = f"[NoFace] 얼굴을 인식할 수 없습니다: '{original_filename}'"
                elif result_label == "Error":
                    return Response(json.dumps({"error": "이미지 분석 중 오류 발생"}, ensure_ascii=False), mimetype='application/json'), 500
                else:
                    result = f"[{result_label}] 이미지 '{original_filename}' 분석 완료 (score: {score:.4f})"

                new_entry = Image(file_path=filepath, result=result, user_id=user_id)
                db.session.add(new_entry)
                db.session.commit()

                response_data = {
                    "message": "파일 및 텍스트 업로드 완료",
                    "file_path": url_for('main.uploaded_file', filename=unique_filename, _external=True),
                    "result": result
                }
                return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json'), 200

            except Exception as e:
                error_msg = f"이미지 처리 중 오류 발생: {str(e)}"
                return Response(json.dumps({"error": error_msg}, ensure_ascii=False), mimetype='application/json'), 500

        return Response(json.dumps({"error": "허용되지 않는 파일 형식입니다."}, ensure_ascii=False), mimetype='application/json'), 400

    elif text_data:
        result = f"텍스트 '{text_data}' 분석 완료"
        new_entry = Image(file_path="text_entry", result=result, user_id=user_id)
        db.session.add(new_entry)
        db.session.commit()

        return Response(json.dumps({"message": "텍스트 저장 완료", "result": result}, ensure_ascii=False), mimetype='application/json'), 201

    return Response(json.dumps({"error": "파일 또는 텍스트를 제공해야 합니다."}, ensure_ascii=False), mimetype='application/json'), 400


@web_bp.route('/upload_web', methods=['POST'])
@login_required
def upload_web():
    if "image" not in request.files:
        return render_template("result.html",
                               error="이미지가 업로드되지 않았습니다.",
                               result=None,
                               file_path=None)

    file = request.files["image"]
    if file.filename == "":
        return render_template("result.html",
                               error="파일 이름이 없습니다.",
                               result=None,
                               file_path=None)

    if allowed_file(file.filename):
        filename = secure_filename(file.filename)
        if "." not in filename:
            filename += ".jpg"

        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(upload_folder, unique_filename)

        try:
            file.save(filepath)
            resize_image(filepath)
            result_label, score, _ = detect_and_classify(filepath)

            if result_label == "NoFace":
                result = "얼굴을 인식할 수 없습니다."
            elif result_label == "Error":
                result = "이미지 분석 중 오류 발생"
            else:
                result = f"{result_label} (score: {score:.4f})"

            new_entry = Image(file_path=filepath, result=result, user_id=current_user.id)
            db.session.add(new_entry)
            db.session.commit()

            return render_template("result.html",
                                   error=None,
                                   result=result,
                                   file_path=url_for('web.uploaded_file', filename=unique_filename))
        except Exception as e:
            return render_template("result.html",
                                   error=f"파일 처리 중 오류가 발생했습니다: {str(e)}",
                                   result=None,
                                   file_path=None)

    # 허용되지 않는 확장자
    return render_template("result.html",
                           error="허용되지 않는 파일 형식입니다. (jpg, jpeg, png만 가능)",
                           result=None,
                           file_path=None)



@web_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(upload_folder, filename)

@nocache
@web_bp.route('/images')
@login_required
def images():
    # 로그인한 사용자의 이미지만 조회
    image_entries = ImageModel.query.filter_by(user_id=current_user.id).all()

    processed_entries = [{
        'id': img.id,
        'file_name': os.path.basename(img.file_path),
        'result': img.result,
        'url': url_for('web.uploaded_file', filename=os.path.basename(img.file_path), _external=True)
    } for img in image_entries]

    return render_template('images.html', image_entries=processed_entries)


@nocache
@web_bp.route('/delete/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    image = Image.query.get(image_id)
    if not image:
        return Response(json.dumps({"error": "이미지를 찾을 수 없습니다."}, ensure_ascii=False), mimetype='application/json'), 404

    file_path = image.file_path
    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass

    db.session.delete(image)
    db.session.commit()

    remaining_images = Image.query.all()
    images_data = [{
        "id": img.id,
        "file_name": os.path.basename(img.file_path),
        "result": img.result
    } for img in remaining_images]

    return Response(json.dumps({"message": "삭제가 완료 되었습니다", "images": images_data}, ensure_ascii=False), mimetype='application/json'), 200


@web_bp.route('/')
@nocache
def index():
    logged_in = 'user_id' in session
    username = session.get('username') if logged_in else None
    return render_template('index.html')


@web_bp.route('/mypage')
@login_required
def mypage():
    return render_template('mypage.html')

from flask import request, render_template, url_for


@web_bp.route('/upload_result')
def upload_result():
    file_path = request.args.get('file_path')  # URL 쿼리로 받음
    result = request.args.get('result')

    # file_path는 절대 URL이므로 이미지 src에 바로 사용 가능
    return render_template('result.html', file_path=file_path, result=result)
