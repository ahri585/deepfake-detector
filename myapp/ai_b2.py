# myapp/ai.py
import os
import io
import cv2
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms, models
import numpy as np
import logging

# -----------------------
# 기본 설정
# -----------------------
logger = logging.getLogger(__name__)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ★ 실제 체크포인트(.pth) 파일 경로로 맞춰줘!
#   (폴더가 아니라 파일이어야 함)
MODEL_PATH = "/home/ubuntu/deepfake-detector/myapp/models/dm2.pth"

# EfficientNet-B3 기본 입력 크기(학습과 동일해야 함)
IMG_SIZE = 300

# 전처리(학습과 동일)
transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

# 얼굴 탐지기(Haar)
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# -----------------------
# 모델 정의 (state_dict 로드 대비)
# -----------------------
class DeepFakeDetector(torch.nn.Module):
    def __init__(self, pretrained=False):
        super(DeepFakeDetector, self).__init__()
        self.backbone = models.efficientnet_b3(pretrained=pretrained)
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = torch.nn.Linear(in_features, 2)

    def forward(self, x):
        return self.backbone(x)

# -----------------------
# 지연 로딩: 최초 호출 시 한 번만 로드
# - 전체 모델(.pt/.pth) & state_dict(.pth) 모두 지원
# - PyTorch 2.6: weights_only=False 명시
# -----------------------
_model = None

def _ensure_model():
    global _model
    if _model is not None:
        return _model

    if not os.path.isfile(MODEL_PATH):
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

    logger.info(f"[ai] loading model from {MODEL_PATH}")
    obj = torch.load(MODEL_PATH, map_location=device, weights_only=False)

    # 1) 전체 모델 객체로 저장된 경우 (예: timm.models.efficientnet.EfficientNet)
    if isinstance(obj, torch.nn.Module):
        m = obj

    # 2) state_dict / checkpoint(dict) 저장본인 경우
    elif isinstance(obj, dict):
        m = DeepFakeDetector(pretrained=False)
        state_dict = obj.get("state_dict", obj)
        # DataParallel로 저장된 경우 'module.' 제거
        if any(k.startswith("module.") for k in state_dict.keys()):
            state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
        missing, unexpected = m.load_state_dict(state_dict, strict=False)
        if unexpected:
            logger.warning(f"[ai] Unexpected keys in state_dict: {unexpected}")
        if missing:
            logger.warning(f"[ai] Missing keys in state_dict: {missing}")

    else:
        raise RuntimeError(f"Unsupported checkpoint type: {type(obj)}")

    m.eval().to(device)
    _model = m
    logger.info("[ai] model loaded and ready")
    return _model

# -----------------------
# 내부 유틸
# -----------------------
def _predict_pil(pil_img: Image.Image):
    """
    PIL 이미지(얼굴 crop) -> (label, confidence)
    ※ 학습 라벨 순서가 [Fake, Real]이라고 가정
      (반대면 아래 인덱스만 바꿔주면 됨)
    """
    x = transform(pil_img).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = _ensure_model()(x)
        probs = F.softmax(logits, dim=1).cpu().numpy()[0]  # shape: [2]
    fake_prob, real_prob = float(probs[0]), float(probs[1])
    if fake_prob >= real_prob:
        return "Fake", fake_prob
    else:
        return "Real", real_prob

# -----------------------
# 외부에서 호출하는 함수 (routes.py가 기대하는 시그니처)
# -----------------------
def detect_and_classify(image_path: str):
    """
    단일 이미지 파일 경로 입력 -> (label, score, image_path) 반환
    label ∈ {"Real","Fake","NoFace","Error"}
    """
    try:
        original = cv2.imread(image_path)
        if original is None:
            logger.error(f"[ai] cv2.imread() failed: {image_path}")
            return "Error", 0.0, image_path

        if face_cascade.empty():
            logger.error("[ai] Haar cascade failed to load")
            # 얼굴 검출기가 비면 전체 이미지로라도 시도할 수 있지만
            # 일단 Error로 반환
            return "Error", 0.0, image_path

        gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        # 얼굴 미탐지
        if len(faces) == 0:
            return "NoFace", 0.0, image_path

        # 여러 얼굴 중 가장 확신 높은 결과 사용
        best_label, best_conf = "Unknown", 0.0
        for (x, y, w, h) in faces:
            face_img = original[y:y+h, x:x+w]
            # OpenCV(BGR) -> PIL(RGB)
            face_pil = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
            label, conf = _predict_pil(face_pil)
            if conf > best_conf:
                best_label, best_conf = label, conf

        return best_label, float(best_conf), image_path

    except Exception as e:
        logger.exception(f"[ai] detect_and_classify exception: {e}")
        return "Error", 0.0, image_path

