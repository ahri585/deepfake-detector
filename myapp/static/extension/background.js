function createContextMenu() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: "checkDeepfake",
      title: "Check Deepfake",
      contexts: ["image"]
    });
  });
}

// 설치 시
chrome.runtime.onInstalled.addListener(() => {
  createContextMenu();
});

// 브라우저 시작 시
chrome.runtime.onStartup.addListener(() => {
  createContextMenu();
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "checkDeepfake") {
    const imageUrl = info.srcUrl;

    fetch("https://aiholmez.com/api/detect-upload", {
      method: "POST",
      body: createFormData(imageUrl)
    })
    .then(response => response.json())
    .then(data => {
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: (responseData) => {
          alert(`딥페이크 분석 결과:\n결과: ${responseData.label}\n신뢰도: ${(responseData.score * 100).toFixed(2)}%`);
        },
        args: [data]
      });
    })
    .catch(error => console.error("API 호출 오류:", error));
  }
});

function createFormData(imageUrl) {
  const formData = new FormData();
  formData.append("image_url", imageUrl);
  return formData;
}

