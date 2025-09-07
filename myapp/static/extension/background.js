// background.js (MV3 통합본) — URL도 /api/detect-upload 로 전송

const API_BASE = "https://aiholmez.com/api";
const DETECT_ENDPOINT = `${API_BASE}/detect-upload`;

// 컨텍스트 메뉴 생성
function createContextMenu() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: "checkDeepfake",
      title: "Check Deepfake",
      contexts: ["image"]
    });
  });
}

chrome.runtime.onInstalled.addListener(createContextMenu);
chrome.runtime.onStartup.addListener(createContextMenu);

// 결과 팝업 열기
function openResultPopup() {
  chrome.windows.create({
    url: chrome.runtime.getURL("result.html"),
    type: "popup",
    width: 500,
    height: 600,
    state: "normal"
  });
}

// 안전한 JSON 파싱 (HTML 응답 등 대비)
async function safeParseJSON(res) {
  try {
    return await res.json();
  } catch (_) {
    const text = await res.text();
    try {
      return JSON.parse(text);
    } catch (e2) {
      return {
        label: "Error",
        result: `서버에서 유효한 JSON 응답을 받지 못했습니다.`,
        raw: text,
        score: 0.0
      };
    }
  }
}

// 타임아웃 지원 fetch (AbortController)
async function fetchWithTimeout(resource, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(resource, { ...options, signal: controller.signal });
    return res;
  } finally {
    clearTimeout(id);
  }
}

// 컨텍스트 메뉴 클릭 핸들러
chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId !== "checkDeepfake") return;

  const imageUrl = info.srcUrl;
  if (!imageUrl) {
    await chrome.storage.local.set({
      lastResult: { label: "Error", result: "이미지 URL을 찾지 못했습니다.", score: 0.0 },
      lastImage: null,
      lastAt: Date.now()
    });
    return openResultPopup();
  }

  console.log("[AI Holmez] 선택한 이미지 URL:", imageUrl);

  const formData = new FormData();
  // /api/detect-upload는 FormData의 image_url 분기를 지원
  formData.append("image_url", imageUrl);

  try {
    const response = await fetchWithTimeout(DETECT_ENDPOINT, { method: "POST", body: formData }, 15000);

    let data = await safeParseJSON(response);

    // HTTP 에러 상태코드면 메시지 보강
    if (!response.ok) {
      data = {
        label: data?.label || "Error",
        result: data?.error || `요청 실패 (status ${response.status})`,
        score: typeof data?.score === "number" ? data.score : 0.0
      };
    }

    // 라벨 누락 시 방어
    if (!data.label && !data.error) {
      data = {
        label: "Error",
        result: "라벨이 없는 응답입니다.",
        score: 0.0
      };
    }

    await chrome.storage.local.set({
      lastResult: data,
      lastImage: imageUrl,
      lastAt: Date.now()
    });

    openResultPopup();

  } catch (error) {
    console.error("[AI Holmez] API 호출 오류:", error);
    await chrome.storage.local.set({
      lastResult: {
        label: "Error",
        result: `API 호출 실패: ${error.message || String(error)}`,
        score: 0.0
      },
      lastImage: imageUrl,
      lastAt: Date.now()
    });
    openResultPopup();
  }
});

