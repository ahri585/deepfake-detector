document.addEventListener("DOMContentLoaded", async () => {
  const resultText = document.getElementById("resultText");
  const scoreText = document.getElementById("scoreText");
  const previewImage = document.getElementById("previewImage");

  // ✅ storage에서 결과와 이미지 URL 불러오기
  const { lastResult, lastImage } = await chrome.storage.local.get(["lastResult", "lastImage"]);

  // ✅ 결과 없으면 기본 메시지
  if (!lastResult) {
    resultText.textContent = "결과 데이터를 불러올 수 없습니다.";
    resultText.className = "result Error";
    previewImage.style.display = "none";
    scoreText.textContent = "신뢰도: -";
    return;
  }

  const { label, score, result } = lastResult;

  // ✅ 이미지 미리보기
  if (lastImage) {
    previewImage.src = lastImage;
  } else {
    previewImage.style.display = "none";
  }

  // ✅ 결과 강조 (색상 반영)
  resultText.textContent = result || "결과 없음";
  resultText.className = `result ${label}`;

  // ✅ 신뢰도 표시
  scoreText.textContent = score !== undefined ? `신뢰도: ${(score * 100).toFixed(2)}%` : "신뢰도: -";
});

