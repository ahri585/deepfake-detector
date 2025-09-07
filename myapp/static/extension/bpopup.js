// popup.js — 파일 + URL 업로드 통합본
const API_BASE = "https://aiholmez.com/api";
const DETECT_ENDPOINT = `${API_BASE}/detect-upload`;

const imageInput = document.getElementById('imageInput');
const urlInput = document.getElementById('urlInput');
const previewDiv = document.getElementById('preview');
const resultDiv = document.getElementById('result');
const urlForm = document.getElementById('urlForm');

// 파일 업로드
imageInput?.addEventListener('change', function (event) {
  const file = event.target.files[0];
  if (!file) return;

  // 로컬 미리보기(즉시 피드백) - 서버 응답 오면 서버 저장본으로 교체
  const reader = new FileReader();
  reader.onload = e => {
    previewDiv.innerHTML = `<img src="${e.target.result}" alt="업로드(임시)" />`;
  };
  reader.readAsDataURL(file);

  const formData = new FormData();
  formData.append('image', file);

  resultDiv.textContent = "분석 중...";

  fetch(DETECT_ENDPOINT, { method: 'POST', body: formData })
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        resultDiv.textContent = `오류: ${data.error}`;
      } else {
        const scoreText = data.score !== undefined ? ` (신뢰도: ${(data.score * 100).toFixed(2)}%)` : '';
        resultDiv.textContent = `결과: ${data.result}${scoreText}`;
      }
      // 서버 저장본이 오면 교체
      if (data.preview_url) {
        previewDiv.innerHTML = `<img src="${data.preview_url}" alt="서버 저장본" />`;
      }
      const imgSrcForHistory = data.preview_url || "(local file)";
      chrome.storage?.local?.set({ lastResult: data, lastImage: imgSrcForHistory, lastAt: Date.now() });
    })
    .catch(err => {
      resultDiv.textContent = `네트워크 오류: ${err}`;
    });
});

// URL 검사
urlForm?.addEventListener('submit', function (event) {
  event.preventDefault();
  const url = urlInput.value.trim();
  if (!url) {
    resultDiv.textContent = "URL을 입력하세요.";
    return;
  }

  // 먼저 원본 URL로 임시 미리보기(응답 오면 서버 저장본으로 교체)
  previewDiv.innerHTML = `<img src="${url}" alt="원본 URL(임시)" />`;

  const formData = new FormData();
  formData.append('image_url', url);

  resultDiv.textContent = "분석 중...";

  fetch(DETECT_ENDPOINT, { method: 'POST', body: formData })
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        resultDiv.textContent = `오류: ${data.error}`;
      } else {
        const scoreText = data.score !== undefined ? ` (신뢰도: ${(data.score * 100).toFixed(2)}%)` : '';
        resultDiv.textContent = `결과: ${data.result}${scoreText}`;
      }
      // 서버 저장본이 있으면 그걸로 교체
      if (data.preview_url) {
        previewDiv.innerHTML = `<img src="${data.preview_url}" alt="서버 저장본" />`;
      } else {
        // 저장본이 없으면 임시(원본 URL) 유지 + 안내
        // resultDiv.textContent += " (원격 다운로드 차단으로 저장본 없음)";
      }
      const imgSrcForHistory = data.preview_url || url;
      chrome.storage?.local?.set({ lastResult: data, lastImage: imgSrcForHistory, lastAt: Date.now() });
    })
    .catch(err => {
      resultDiv.textContent = `네트워크 오류: ${err}`;
    });
});

