document.getElementById('imageInput').addEventListener('change', function(event) {
  const file = event.target.files[0];
  const previewDiv = document.getElementById('preview');
  const resultDiv = document.getElementById('result');

  if (!file) return;

  // ✅ 이미지 미리보기
  const reader = new FileReader();
  reader.onload = e => {
    previewDiv.innerHTML = `<img src="${e.target.result}" alt="업로드 이미지" style="max-width: 100%; height: auto;">`;
  };
  reader.readAsDataURL(file);

  // ✅ API 호출 준비
  const formData = new FormData();
  formData.append('image', file);

  resultDiv.textContent = "분석 중...";

  fetch('https://aiholmez.com/api/detect-upload', {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      resultDiv.textContent = `오류: ${data.error}`;
    } else {
      const scoreText = data.score !== undefined ? ` (신뢰도: ${(data.score * 100).toFixed(2)}%)` : '';
      resultDiv.textContent = `결과: ${data.result}${scoreText}`;
    }
  })
  .catch(err => {
    resultDiv.textContent = `네트워크 오류: ${err}`;
  });
});

