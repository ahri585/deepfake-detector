// result.js — chrome.storage.local에 저장된 분석 결과 표시 (preview_url 우선)

document.addEventListener("DOMContentLoaded", async () => {
  const imgEl = document.getElementById("previewImage");
  const resultEl = document.getElementById("resultText");
  const scoreEl = document.getElementById("scoreText");

  // 1) 저장된 값 읽기
  let stored = {};
  try {
    stored = await chrome.storage.local.get(["lastResult", "lastImage", "lastAt"]);
  } catch (e) {
    // 만약 Promise 미지원 환경이면 콜백 방식으로 대체 필요
  }
  const lastResult = stored.lastResult;
  const lastImage = stored.lastImage;

  // 2) 기본값
  if (!lastResult) {
    imgEl.src = "icon.png";
    resultEl.textContent = "결과 없음";
    resultEl.className = "result";
    scoreEl.textContent = "신뢰도: -";
    return;
  }

  // 3) 이미지 소스 결정: preview_url > lastImage > icon.png
  const previewUrl = typeof lastResult.preview_url === "string" && lastResult.preview_url.trim() !== ""
    ? lastResult.preview_url
    : null;

  let imgSrc = previewUrl;
  if (!imgSrc) {
    if (typeof lastImage === "string" && lastImage.trim() !== "") {
      imgSrc = (lastImage === "(local file)") ? "icon.png" : lastImage;
    } else {
      imgSrc = "icon.png";
    }
  }
  imgEl.src = imgSrc;

  // 4) 라벨/메시지/스타일
  const label = (lastResult.label || lastResult.result || "결과 없음").trim();
  let msg = label;
  let cls = "result";

  switch (label) {
    case "Real":
      msg = "Real (진짜로 판별됨)";
      cls += " Real";
      break;
    case "Fake":
      msg = "Fake (가짜로 판별됨)";
      cls += " Fake";
      break;
    case "NoFace":
      msg = "얼굴을 인식할 수 없습니다.";
      cls += " NoFace";
      break;
    case "Uncertain":
      msg = "판별 확신이 낮습니다.";
      cls += " Uncertain";
      break;
    case "Error":
      msg = lastResult.error ? `오류: ${lastResult.error}` : "이미지 분석 중 오류 발생";
      cls += " Error";
      break;
    default:
      // 그대로 msg/cls 유지
      break;
  }

  resultEl.textContent = msg;
  resultEl.className = cls;

  // 5) 신뢰도 표시
  if (typeof lastResult.score === "number") {
    scoreEl.textContent = `신뢰도: ${(lastResult.score * 100).toFixed(2)}%`;
  } else {
    scoreEl.textContent = "신뢰도: -";
  }

  // 6) 힌트: preview_url이 없어서 원본 URL/아이콘으로 대체 중이면 title로 알려주기
  if (!previewUrl) {
    imgEl.title = "서버 저장본(preview_url)이 없어 임시 소스를 표시합니다.";
  }
});

