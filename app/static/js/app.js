document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const filePreviewCard = document.getElementById('filePreviewCard');
  const fileThumbnail = document.getElementById('fileThumbnail');
  const fileName = document.getElementById('fileName');
  const fileSize = document.getElementById('fileSize');
  const btnRemove = document.getElementById('btnRemove');
  const uploadForm = document.getElementById('uploadForm');
  const submitBtn = document.getElementById('submitBtn');
  const submitBtnText = document.getElementById('submitBtnText');
  const loadingIndicator = document.getElementById('loadingIndicator');
  const resultsContainer = document.getElementById('resultsContainer');
  const resultImage = document.getElementById('resultImage');
  const extractedContent = document.getElementById('extractedContent');
  const errorAlert = document.getElementById('errorAlert');
  const errorMessage = document.getElementById('errorMessage');
  const commentsList = document.getElementById('commentsList');
  const additionalComments = document.getElementById('additionalComments');
  let currentRawText = '';

  // ── Helpers ────────────────────────────────────────────────────────────────

  function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function showError(msg) {
    errorMessage.textContent = msg;
    errorAlert.style.display = 'flex';
    errorAlert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function hideError() {
    errorAlert.style.display = 'none';
  }

  // ── File selection ─────────────────────────────────────────────────────────

  function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) {
      showError('Please select a valid image file (PNG, JPG, WEBP, etc.).');
      return;
    }
    hideError();
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);
    const reader = new FileReader();
    reader.onload = (e) => {
      fileThumbnail.src = e.target.result;
      dropzone.style.display = 'none';
      filePreviewCard.style.display = 'flex';
      submitBtn.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  function resetFile() {
    fileInput.value = '';
    fileThumbnail.src = '';
    dropzone.style.display = 'block';
    filePreviewCard.style.display = 'none';
    submitBtn.disabled = true;
  }

  // ── Dropzone events ────────────────────────────────────────────────────────

  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      handleFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => handleFile(fileInput.files[0]));
  btnRemove.addEventListener('click', (e) => { e.stopPropagation(); resetFile(); });

  // ── Form submit ────────────────────────────────────────────────────────────

  uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideError();
    additionalComments.style.display = 'none';
    commentsList.replaceChildren();

    if (!fileInput.files || fileInput.files.length === 0) {
      showError('Please select an image to upload.');
      return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    hideError();
    submitBtn.disabled = true;
    submitBtnText.textContent = 'Extracting...';
    loadingIndicator.style.display = 'block';
    resultsContainer.style.display = 'none';

    try {
      const response = await fetch('/extract', { method: 'POST', body: formData });
      const data = await response.json();

      if (!data.success) throw new Error(data.error || 'Extraction failed.');

      currentRawText = JSON.stringify(data.data, null, 2);

      resultImage.src = data.image_base64;
      extractedContent.textContent = currentRawText;

      loadingIndicator.style.display = 'none';
      resultsContainer.style.display = 'grid';
      resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });

      const issues = basicValidationCheck(data.data);
      if (issues.length > 0) {
        for (const msg of issues) {
          const li = document.createElement('li');
          li.textContent = msg;
          commentsList.appendChild(li);
        }
        additionalComments.style.display = 'block';
      }

    } catch (err) {
      loadingIndicator.style.display = 'none';
      showError(err.message);
    } finally {
      submitBtn.disabled = false;
      submitBtnText.textContent = 'Extract Invoice JSON';
    }
  });

  // Client-side Validation
  const differs = (a, b) => !(Math.abs(a - b) <= 0.01);

  function basicValidationCheck(data) {
    if (!data.isInvoice) return ['The uploaded image is not a valid invoice.'];

    const issues = [];
    let itemsSum = 0;

    for (const item of data.items ?? []) {
      const expected = item.quantity * item.unit_price;
      if (differs(expected, item.line_total)) {
        issues.push(
          `${item.description}: ${item.quantity} × ${item.unit_price} = ${expected}, but the line total is ${item.line_total}.`
        );
      }
      itemsSum += item.line_total ?? 0;
    }

    if (differs(data.subtotal, itemsSum)) {
      issues.push(`Subtotal is ${data.subtotal}, but the line totals add up to ${itemsSum}.`);
    }

    const expectedTotal = (data.subtotal ?? 0) + (data.vat ?? 0) - (data.discount ?? 0);
    if (differs(data.total_amount, expectedTotal)) {
      issues.push(`Total is ${data.total_amount}, but subtotal + VAT − discount = ${expectedTotal}.`);
    }

    return issues;
  }


});
