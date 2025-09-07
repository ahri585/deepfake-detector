// popup.js — 파일 + URL 업로드 통합본 (preview_url 우선, 에러시 미리보기 제거)
const API_BASE = "https://aiholmez.com/api";
const DETECT_ENDPOINT = `${API_BASE}/detect-upload`;

const imageInput = document.getElementById("imageInput");
const urlInput = document.getElementById("urlInput");
const previewDiv = document.getElementById("preview");
const resultDiv = document.getElementById("result");
const urlForm = document.getElementById("urlForm");

// ---------- helpers ----------
function setPreview(src, alt = "미리보기") {
  if (!previewDiv) return;
  if (!src) {
    previewDiv.innerHTML = "";
    return;
  }
  previewDiv.innerHTML = `<img src="${src}" alt="${alt}" style="max-width:100%; height:auto;">`;
}

function setResultFromJson(json) {
  if (!json) return;

  // 결과 메시지
  if (json.error) {
    resultDiv.textContent = `오류: ${json.error}`;
  } else {
    const label = json.label || json.result || "결과 없음";
    const scoreText =
      typeof json.score === "number"
        ? ` (신뢰도: ${(json.score * 100).toFixed(2)}%)`
        : "";
    resultDiv.textContent = `결과: ${label}${scoreText}`;
  }

  // 미리보기: preview_url 있을 때만 표시, 없으면 비움
  if (json.preview_url) {
    setPreview(json.preview_url, "서버 저장본");
  } else {
    setPreview(""); // 결과 없음/오류 등은 이미지 제거
  }

  // 히스토리 저장: preview_url 우선
  if (chrome?.storage?.local) {
    const imgSrcForHistory = json.preview_url || "";
    chrome.storage.local.set({
      lastResult: json,
      lastImage: imgSrcForHistory,
      lastAt: Date.now(),
    });
  }
}

async function fetchJsonSafely(url, options) {
  const res = await fetch(url, options);
  let data;
  try {
    data = await res.json();
  } catch {
    const txt = await res.text();
    data = { error: `유효한 JSON이 아닙니다. (status ${res.status})`, raw: txt };
  }
  if (!res.ok) {
    data.error ||= `요청 실패 (status ${res.status})`;
  }
  return data;
}

// ---------- 파일 업로드 ----------
imageInput?.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;

  // (임시) 로컬 미리보기 — 응답 오면 서버 저장본/제거로 교체
  const reader = new FileReader();
  reader.onload = (e) => setPreview(e.target.result, "업로드(임시)");
  reader.readAsDataURL(file);

  // API 호출
  const formData = new FormData();
  formData.append("image", file);
  resultDiv.textContent = "분석 중...";

  try {
    const data = await fetchJsonSafely(DETECT_ENDPOINT, {
      method: "POST",
      body: formData,
    });
    setResultFromJson(data);
  } catch (err) {
    setPreview(""); // 네트워크 오류 시 미리보기 제거
    resultDiv.textContent = `네트워크 오류: ${String(err)}`;
  }
});

// ---------- URL 검사 ----------
urlForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = urlInput.value.trim();
  if (!url) {
    resultDiv.textContent = "URL을 입력하세요.";
    return;
  }

  // 간단 URL 유효성 체크
  try {
    new URL(url);
  } catch {
    resultDiv.textContent = "유효한 URL이 아니에요.";
    setPreview("");
    return;
  }

  // (임시) 원본 URL 미리보기 — 응답 오면 서버 저장본/제거로 교체
  setPreview(url, "원본 URL(임시)");
  resultDiv.textContent = "분석 중...";

  const formData = new FormData();
  formData.append("image_url", url);

  try {
    const data = await fetchJsonSafely(DETECT_ENDPOINT, {
      method: "POST",
      body: formData,
    });
    setResultFromJson(data);
  } catch (err) {
    setPreview(""); // 네트워크 오류 시 미리보기 제거
    resultDiv.textContent = `네트워크 오류: ${String(err)}`;
  }
});

