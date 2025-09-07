// result.js — chrome.storage.local에 저장된 분석 결과 표시 (preview_url 우선, 실패/빈결과면 이미지 숨김)

document.addEventListener("DOMContentLoaded", async () => {
  const imgEl = document.getElementById("previewImage");
  const resultEl = document.getElementById("resultText");
  const scoreEl = document.getElementById("scoreText");

  // 1) 저장값 로드
  let stored = {};
  try {
    stored = await chrome.storage.local.get(["lastResult", "lastAt"]);
  } catch (_) {
    // 콜백 방식 필요하면 별도 처리
  }
  const lastResult = stored.lastResult;

  // 2) 기본값 (저장된 결과 없음)
  if (!lastResult) {
    hideImage(imgEl);
    setResult("결과 없음", null);
    return;
  }

  // 3) 라벨/메시지/스타일
  const label = (lastResult.label || lastResult.result || "결과 없음").trim();
  const scoreNum = (typeof lastResult.score === "number") ? lastResult.score : null;

  // 4) 이미지 표시 정책
  //   - preview_url 있을 때만 표시
  //   - 다음 라벨들은 이미지 숨김 유지: 결과 없음 / Error / NoFace / Uncertain
  const previewUrl = (typeof lastResult.preview_url === "string" && lastResult.preview_url.trim() !== "")
    ? lastResult.preview_url
    : null;

  const HIDE_IMAGE_LABELS = new Set(["결과 없음", "Error", "NoFace", "Uncertain"]);

  if (!previewUrl || HIDE_IMAGE_LABELS.has(label)) {
    hideImage(imgEl, !previewUrl);
  } else {
    showImage(imgEl, previewUrl);
  }

  // 5) 결과/신뢰도 렌더
  setResult(label, scoreNum, lastResult.error);

  // 6) preview_url이 없으면 힌트 제공
  if (!previewUrl) {
    imgEl.title = "서버 저장본(preview_url)이 없어 이미지를 표시하지 않습니다.";
  } else {
    imgEl.removeAttribute("title");
  }

  // ---- 유틸 함수들 ----
  function showImage(el, src) {
    if (!el) return;
    el.src = src;
    el.style.display = "block";
  }

  function hideImage(el, removeSrc = true) {
    if (!el) return;
    if (removeSrc) el.removeAttribute("src");
    el.style.display = "none";
  }

  function setResult(lbl, score, errMsg) {
    let msg = lbl;
    let cls = "result";

    switch (lbl) {
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
        msg = errMsg ? `오류: ${errMsg}` : "이미지 분석 중 오류 발생";
        cls += " Error";
        break;
      default:
        // 그대로 유지
        break;
    }

    resultEl.textContent = msg;
    resultEl.className = cls;

    if (typeof score === "number") {
      scoreEl.textContent = `신뢰도: ${(score * 100).toFixed(2)}%`;
    } else {
      scoreEl.textContent = "신뢰도: -";
    }
  }
});

