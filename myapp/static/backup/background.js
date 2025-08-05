chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "checkDeepfake",
    title: "Check Deepfake",
    contexts: ["image"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "checkDeepfake") {
    chrome.storage.local.set({ deepfakeResult: "분석 중..." }); // 로딩 상태
    fetch("https://aiholmez.com/api/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_url: info.srcUrl })
    })
    .then(response => response.json())
    .then(data => {
      const resultText = data.result ? `결과: ${data.result}` : "오류 발생";
      chrome.storage.local.set({ deepfakeResult: resultText });
    })
    .catch(err => {
      chrome.storage.local.set({ deepfakeResult: `네트워크 오류: ${err}` });
    });
  }
});

