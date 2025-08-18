# ai.py — 통합판 (학습=추론 아님, 판별용)
import os
import cv2
import torch
import torch.nn.functional as F
from torchvision import transforms, models
from PIL import Image, ImageOps
import numpy as np

# =========================
# ✅ 고정 설정/옵션
# =========================
# 모델 파일(.pth) 경로 — 너 파일명으로 바꿔줘!
MODEL_PATH = "/home/ubuntu/deepfake-detector/myapp/models/dm2.pth"
# MODEL_PATH = "/home/ubuntu/deepfake-detector/myapp/models/dm2"  # ← 이게 '폴더'면 안 됨. 파일이어야 함.

# 학습자가 확정해준 매핑
FAKE_IDX, REAL_IDX = 0, 1
CLASS_NAMES = ["Fake", "Real"]

# 전처리/크롭/임계값
USE_FACE_CROP = False          # 지표 코드와 맞추려면 False(전체 프레임). 얼굴만 쓰려면 True
SELECT_LARGEST_FACE = True     # 여러 얼굴 중 가장 큰 얼굴 선택
THRESH = None                  # 예: 0.6 넣으면 확신 낮으면 'Uncertain'로 반환

# (선택) 완전 동일 결과가 중요할 때 결정론 모드
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False

# =========================
# ✅ 모델 정의/로드
# =========================
class DeepFakeDetector(torch.nn.Module):
    def __init__(self, pretrained=False):
        super(DeepFakeDetector, self).__init__()
        self.backbone = models.efficientnet_b3(pretrained=pretrained)
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = torch.nn.Linear(in_features, 2)

    def forward(self, x):
        return self.backbone(x)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def _build_model_from_state_dict(state_dict: dict) -> torch.nn.Module:
    model = DeepFakeDetector(pretrained=False)
    # DDP 저장 시 'module.' 접두어 제거
    if any(k.startswith("module.") for k in state_dict.keys()):
        state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    if unexpected:
        print(f"[ai] ⚠ unexpected keys: {unexpected}")
    if missing:
        print(f"[ai] ⚠ missing keys: {missing}")
    return model

def _load_model():
    # PyTorch 2.6부터 weights_only=True 기본이라 타입 대응
    ckpt = None
    try:
        ckpt = torch.load(MODEL_PATH, map_location=device, weights_only=True)
    except TypeError:
        # 구버전 호환
        ckpt = torch.load(MODEL_PATH, map_location=device)
    except Exception as e:
        # 안전 로드 실패 시, 경고 후 일반 로드 재시도
        print(f"[ai] safe load 실패: {e}\n[ai] weights_only=False 로 재시도합니다(신뢰 가능한 파일만 사용).")
        ckpt = torch.load(MODEL_PATH, map_location=device, weights_only=False)

    if isinstance(ckpt, torch.nn.Module):
        model = ckpt
    elif isinstance(ckpt, dict):
        state = ckpt.get("state_dict", ckpt)
        model = _build_model_from_state_dict(state)
    else:
        raise RuntimeError(f"[ai] 지원하지 않는 체크포인트 타입: {type(ckpt)}")

    model.eval().to(device)
    # 매핑 로그 한 번만 출력
    if not getattr(model, "_printed_mapping", False):
        print(f"[ai] CLASS_MAPPING: {FAKE_IDX}=Fake, {REAL_IDX}=Real")
        model._printed_mapping = True
    return model

model = _load_model()

# =========================
# ✅ 전처리/얼굴 검출
# =========================
transform = transforms.Compose([
    transforms.Resize((300, 300), antialias=True),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def _prep_pil(img_bgr: np.ndarray) -> Image.Image:
    # OpenCV BGR -> RGB, EXIF 회전 보정
    pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    pil = ImageOps.exif_transpose(pil)
    return pil

# =========================
# ✅ 판별 함수 (서비스에서 호출)
# =========================
def detect_and_classify(image_path: str):
    """
    반환: (label:str, confidence:float, image_path:str)
    label ∈ {"Fake","Real","Uncertain","NoFace","Error"}
    """
    try:
        original = cv2.imread(image_path)
        if original is None:
            print(f"❌ 이미지 로딩 실패: {image_path}")
            return "Error", 0.0, image_path

        # --- 얼굴 크롭 정책 ---
        if USE_FACE_CROP:
            gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.2, minNeighbors=4, minSize=(60, 60)
            )
            if len(faces) == 0:
                # 얼굴을 못 찾으면 지표 코드와 동일하게 전체 프레임 사용
                pil = _prep_pil(original)
            else:
                x, y, w, h = (max(faces, key=lambda b: b[2] * b[3])
                              if SELECT_LARGEST_FACE else faces[0])
                face_img = original[y:y + h, x:x + w]
                pil = _prep_pil(face_img)
        else:
            # 지표 코드와 동일: 크롭 없이 전체 프레임
            pil = _prep_pil(original)

        # --- 전처리/추론 ---
        input_tensor = transform(pil).unsqueeze(0).to(device)
        with torch.no_grad():
            output = model(input_tensor)
            prob = F.softmax(output, dim=1)[0]  # 길이 2
            fake_prob = float(prob[FAKE_IDX].item())
            real_prob = float(prob[REAL_IDX].item())
            score = max(fake_prob, real_prob)

            # 임계값(선택): 확신 낮으면 Uncertain
            if THRESH is not None and score < THRESH:
                return "Uncertain", score, image_path

            label = "Fake" if fake_prob >= real_prob else "Real"
            return label, score, image_path

    except Exception as e:
        print(f"[ai] 예외: {e}")
        return "Error", 0.0, image_path

