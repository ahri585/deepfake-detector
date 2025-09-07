from flask import Blueprint, request, Response, send_from_directory, render_template, url_for, session, jsonify, current_app
from werkzeug.utils import secure_filename
from .utils import allowed_file, nocache, is_valid_image  # resize_image 제거 상태 유지
from .models import Image, db, User
from .ai import detect_and_classify
from .models import Image as ImageModel
import os, uuid, json, jwt
from flask_cors import CORS
from flask_login import login_required, current_user
from .app_auth import token_required
import logging, requests
from datetime import datetime

log_dir = "/home/ubuntu/deepfake-detector/logs"
os.makedirs(log_dir, exist_ok=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    file_handler = logging.FileHandler(os.path.join(log_dir, "server.log"))
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
logger.debug("[ROUTES] routes.py (unified: detect-upload only)")

main_bp = Blueprint('main', __name__, url_prefix='/api')
CORS(main_bp)

web_bp = Blueprint('web', __name__)
CORS(web_bp)

upload_folder = '/home/ubuntu/deepfake-detector/myapp/static/uploads'
os.makedirs(upload_folder, exist_ok=True)


@main_bp.route('/upload', methods=['POST'])
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
            original_filename += ".jpg"
        original_filename = secure_filename(original_filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        filepath = os.path.join(upload_folder, unique_filename)

        if is_valid_image(file):
            logger.debug("이미지유효성 검사 통과")
            try:
                logger.debug(f"파일 저장 위치: {filepath}")
                file.save(filepath)
                logger.debug("파일 저장 완료")

                logger.debug(f"detect_and_classify() 호출 준비: {filepath}")
                result_label, score, _ = detect_and_classify(filepath)
                logger.debug(f"분석결과: label={result_label}, score={score:.4f}")

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
                    "file_path": url_for('web.uploaded_file', filename=unique_filename, _external=True),
                    "result": result
                }
                return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json'), 200

            except Exception as e:
                logger.exception("이미지 처리중 오류 발생")
                error_msg = f"이미지 처리 중 오류 발생: {str(e)}"
                return Response(json.dumps({"error": error_msg}, ensure_ascii=False), mimetype='application/json'), 500

        return Response(json.dumps({"error": "허용되지 않는 파일 형식입니다."}, ensure_ascii=False), mimetype='application/json'), 400

    elif text_data:
        result = f"텍스트 '{text_data}' 분석 완료"
        new_entry = Image(file_path="text_entry", result=result, user_id=user_id)
        db.session.add(new_entry)
        db.session.commit()
        return Response(json.dumps({"message": "텍스트 업로드 완료", "result": result}, ensure_ascii=False), mimetype='application/json'), 200


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


@web_bp.route('/upload_result')
def upload_result():
    file_path = request.args.get('file_path')  # URL 쿼리로 받음
    result = request.args.get('result')

    # file_path는 절대 URL이므로 이미지 src에 바로 사용 가능
    return render_template('result.html', file_path=file_path, result=result)


@main_bp.route('/mypage', methods=['GET'])
@token_required
def get_user_info(current_user_id):
    user = User.query.get(current_user_id)
    return jsonify({
        "username": user.username,
        "email": user.email,
    })


@web_bp.route('/extension')
@login_required
def extension():
    return render_template('extension.html')


# ============================
#  통합 엔드포인트 (파일 + URL)
#  POST /api/detect-upload
# ============================
@main_bp.route('/detect-upload', methods=['POST'])
def detect_upload():
    img_path = None
    saved_rel_path = None  # static 기준 상대경로
    try:
        # 1) 파일 업로드
        if "image" in request.files:
            file = request.files["image"]
            if not file or file.filename == "":
                return jsonify({"ok": False, "error": "파일 이름이 없습니다"}), 400

            original = secure_filename(file.filename)
            name, ext = os.path.splitext(original)
            if not ext:
                ext = ".jpg"

            filename = f"{uuid.uuid4().hex}{ext.lower()}"
            # 업로드 폴더: <project>/static/uploads/2025-09-07
            date_folder = datetime.utcnow().strftime("%Y-%m-%d")
            save_dir = os.path.join(current_app.static_folder, "uploads", date_folder)
            os.makedirs(save_dir, exist_ok=True)

            filepath = os.path.join(save_dir, filename)
            file.save(filepath)
            img_path = filepath
            saved_rel_path = f"uploads/{date_folder}/{filename}"  # static 기준

        # 2) URL 업로드(FormData: image_url)
        elif "image_url" in request.form:
            img_url = request.form.get("image_url", "").strip()
            if not img_url:
                return jsonify({"ok": False, "error": "이미지 URL이 없습니다"}), 400

            try:
                headers = {
                    "User-Agent": "Mozilla/5.0",
                    # 필요하면 Referer 도메인 조건부 추가
                    # "Referer": img_url_origin
                }
                r = requests.get(img_url, headers=headers, timeout=8)
                r.raise_for_status()
            except Exception as e:
                return jsonify({"ok": False, "error": f"이미지 다운로드 실패: {e}"}), 400

            ext = guess_ext_from_headers_or_url(r.headers.get("Content-Type"), img_url)  # 아래 util로 커버
            filename = f"url_{uuid.uuid4().hex}{ext}"

            date_folder = datetime.utcnow().strftime("%Y-%m-%d")
            save_dir = os.path.join(current_app.static_folder, "uploads", date_folder)
            os.makedirs(save_dir, exist_ok=True)

            filepath = os.path.join(save_dir, filename)
            with open(filepath, "wb") as f:
                f.write(r.content)
            img_path = filepath
            saved_rel_path = f"uploads/{date_folder}/{filename}"

        else:
            return jsonify({"ok": False, "error": "이미지가 없습니다"}), 400

        # 3) 모델 분석
        try:
            result_label, score, _ = detect_and_classify(img_path)
        except Exception as e:
            current_app.logger.exception("모델 분석 중 예외")
            return jsonify({"ok": False, "error": f"모델 분석 실패: {e}"}), 500

        # 4) 응답(★ preview_url 포함)
        preview_url = url_for('static', filename=saved_rel_path, _external=True)

        if result_label == "NoFace":
            return jsonify({"ok": True, "label": "NoFace", "result": "얼굴을 인식할 수 없습니다.",
                            "score": 0.0, "preview_url": preview_url})
        elif result_label == "Error":
            return jsonify({"ok": False, "label": "Error", "result": "이미지 분석 중 오류 발생",
                            "score": 0.0, "preview_url": preview_url})
        else:
            return jsonify({"ok": True, "label": result_label, "result": result_label,
                            "score": round(float(score), 4), "preview_url": preview_url})
    except Exception as e:
        current_app.logger.exception("detect_upload 함수 예외")
        return jsonify({"ok": False, "error": f"서버 내부 오류: {e}"}), 500


# 간단 util (필요시 파일 상단에 추가)
def guess_ext_from_headers_or_url(content_type: str | None, url: str) -> str:
    # content-type 우선
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
    }
    if content_type and content_type.split(";")[0].strip().lower() in mapping:
        return mapping[content_type.split(";")[0].strip().lower()]
    # URL fallback
    parsed = url.split("?")[0].lower()
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"]:
        if parsed.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


@web_bp.route('/multi', methods=['GET'])
def multi_page():
    return render_template('multi.html')


@main_bp.route('/detect-multi', methods=['POST'])
def detect_multi():
    results = []
    try:
        # 폼에서 넘어온 cleanup 옵션 (체크박스 on → true)
        cleanup = (request.form.get('cleanup', '').lower() in ['1', 'true', 'on', 'yes'])

        if "images" not in request.files:
            return jsonify({"error": "업로드된 이미지가 없습니다."}), 400

        files = request.files.getlist("images")
        if not files:
            return jsonify({"error": "파일이 비어있습니다."}), 400

        for file in files:
            if file.filename == "":
                results.append({"filename": None, "label": "Error", "score": 0.0, "result": "파일 이름 없음"})
                continue

            filename = secure_filename(file.filename)
            unique = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(upload_folder, unique)
            file.save(filepath)

            try:
                result_label, score, _ = detect_and_classify(filepath)

                # 요청이 cleanup이면 파일 삭제
                if cleanup:
                    try:
                        os.remove(filepath)
                    except Exception as e:
                        current_app.logger.warning(f"[multi] 파일 삭제 실패: {e}")

                if result_label == "NoFace":
                    result = "얼굴을 인식할 수 없습니다."
                elif result_label == "Error":
                    result = "이미지 분석 중 오류 발생"
                else:
                    result = f"{result_label} (score: {score:.4f})"

                results.append({
                    "filename": filename,
                    "label": result_label,
                    "score": round(float(score), 4),
                    "result": result,
                    # 미리보기는 cleanup 아닐 때만 제공
                    "url": None if cleanup else url_for('web.uploaded_file', filename=unique, _external=True)
                })
            except Exception as e:
                results.append({
                    "filename": filename,
                    "label": "Error",
                    "score": 0.0,
                    "result": f"처리 오류: {str(e)}"
                })

        summary = {
            "total": len(results),
            "counts": {
                "Real": sum(1 for r in results if r["label"] == "Real"),
                "Fake": sum(1 for r in results if r["label"] == "Fake"),
                "Uncertain": sum(1 for r in results if r["label"] == "Uncertain"),
                "NoFace": sum(1 for r in results if r["label"] == "NoFace"),
                "Error": sum(1 for r in results if r["label"] == "Error"),
            }
        }
        return jsonify({"summary": summary, "results": results}), 200

    except Exception as e:
        current_app.logger.error(f"/api/detect-multi 예외: {e}")
        return jsonify({"error": f"서버 내부 오류: {str(e)}"}), 500

