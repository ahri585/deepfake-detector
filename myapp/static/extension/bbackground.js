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

function openResultPopup() {
  chrome.windows.create({
    url: chrome.runtime.getURL("result.html"),
    type: "popup",
    width: 500,
    height: 600,
    state: "normal"
  });
}

chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId === "checkDeepfake") {
    const imageUrl = info.srcUrl;
    console.log("선택한 이미지 URL:", imageUrl);

    const formData = new FormData();
    formData.append("image_url", imageUrl);

    try {
      const response = await fetch("https://aiholmez.com/api/detect-upload", {
        method: "POST",
        body: formData
      });

      const text = await response.text();
      console.log("API 응답 내용:", text);

      let data;
      try {
        data = JSON.parse(text);
      } catch (err) {
        console.error("JSON 파싱 실패: HTML 응답 가능", err);
        data = {
          label: "Error",
          result: "서버에서 유효한 JSON 응답을 받지 못했습니다.",
          score: 0.0
        };
      }

      await chrome.storage.local.set({ lastResult: data, lastImage: imageUrl });
      openResultPopup();

    } catch (error) {
      console.error("API 호출 오류:", error);
      await chrome.storage.local.set({
        lastResult: {
          label: "Error",
          result: `API 호출 실패: ${error.message}`,
          score: 0.0
        }
      });
      openResultPopup();
    }
  }
});

