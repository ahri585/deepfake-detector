import cv2
import torch
import torch.nn.functional as F
from torchvision import transforms, models
from PIL import Image
import numpy as np


# ✅ 모델 클래스 (학습 시와 동일)
class DeepFakeDetector(torch.nn.Module):
    def __init__(self, pretrained=False):
        super(DeepFakeDetector, self).__init__()
        self.backbone = models.efficientnet_b3(pretrained=pretrained)
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = torch.nn.Linear(in_features, 2)

    def forward(self, x):
        return self.backbone(x)

# ✅ 장치 설정 및 모델 로드
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = DeepFakeDetector()
model.load_state_dict(torch.load("/home/ubuntu/deepfake-detector/myapp/models/deepfake_efficientnetb3_finetuned.pth", map_location=device))
model.eval()
model.to(device)

# ✅ 전처리
transform = transforms.Compose([
    transforms.Resize((300, 300)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

# ✅ 얼굴 탐지 모델 로딩
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# ✅ 이미지 한 장 추론 함수
def detect_and_classify(image_path):
    original = cv2.imread(image_path)
    if original is None:
        print(f"❌ 이미지 로딩 실패: {image_path}")
        return "Error", 0.0, image_path  # 반드시 3개 리턴

    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    # 얼굴 미탐지 시 NoFace 반환
    if len(faces) == 0:
        return "NoFace", 0.0, image_path

    final_label = "Unknown"
    final_confidence = 0.0

    for i, (x, y, w, h) in enumerate(faces):
        face_img = original[y:y+h, x:x+w]
        face_pil = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
        input_tensor = transform(face_pil).unsqueeze(0).to(device)

        with torch.no_grad():
            output = model(input_tensor)
            prob = F.softmax(output, dim=1)
            fake_prob = prob[0][0].item()
            real_prob = prob[0][1].item()
            label = "Fake" if fake_prob > real_prob else "Real"
            confidence = max(fake_prob, real_prob)

        # 마지막 얼굴의 예측을 최종 결과로 사용
        final_label = label
        final_confidence = confidence

    return final_label, final_confidence, image_path


