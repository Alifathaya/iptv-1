/**
 * Photo Clarify — client-side image enhancement
 * Uses unsharp mask, clarity, contrast, and optional upscale.
 */

const MAX_DIMENSION = 2048;

const state = {
  originalImage: null,
  originalWidth: 0,
  originalHeight: 0,
  settings: {
    sharpness: 50,
    clarity: 40,
    contrast: 20,
    brightness: 0,
    denoise: 15,
    upscale: 0,
  },
  preset: 'auto',
  comparePosition: 50,
  processing: false,
};

const els = {
  uploadZone: document.getElementById('uploadZone'),
  fileInput: document.getElementById('fileInput'),
  workspace: document.getElementById('workspace'),
  beforeCanvas: document.getElementById('beforeCanvas'),
  afterCanvas: document.getElementById('afterCanvas'),
  compareContainer: document.getElementById('compareContainer'),
  compareAfter: document.getElementById('compareAfter'),
  compareHandle: document.getElementById('compareHandle'),
  labelBefore: document.getElementById('labelBefore'),
  labelAfter: document.getElementById('labelAfter'),
  presetBtns: document.querySelectorAll('.preset-btn'),
  sliders: {
    sharpness: document.getElementById('sharpness'),
    clarity: document.getElementById('clarity'),
    contrast: document.getElementById('contrast'),
    brightness: document.getElementById('brightness'),
    denoise: document.getElementById('denoise'),
    upscale: document.getElementById('upscale'),
  },
  values: {
    sharpness: document.getElementById('sharpnessValue'),
    clarity: document.getElementById('clarityValue'),
    contrast: document.getElementById('contrastValue'),
    brightness: document.getElementById('brightnessValue'),
    denoise: document.getElementById('denoiseValue'),
    upscale: document.getElementById('upscaleValue'),
  },
  btnDownload: document.getElementById('btnDownload'),
  btnReset: document.getElementById('btnReset'),
  btnNew: document.getElementById('btnNew'),
  processingOverlay: document.getElementById('processingOverlay'),
};

const PRESETS = {
  auto: { sharpness: 50, clarity: 40, contrast: 20, brightness: 0, denoise: 15, upscale: 0 },
  blur: { sharpness: 75, clarity: 55, contrast: 25, brightness: 5, denoise: 25, upscale: 50 },
  document: { sharpness: 85, clarity: 30, contrast: 45, brightness: 10, denoise: 10, upscale: 0 },
  soft: { sharpness: 30, clarity: 25, contrast: 10, brightness: 0, denoise: 30, upscale: 0 },
};

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function scaleDimensions(width, height) {
  const maxSide = Math.max(width, height);
  if (maxSide <= MAX_DIMENSION) return { width, height };

  const scale = MAX_DIMENSION / maxSide;
  return {
    width: Math.round(width * scale),
    height: Math.round(height * scale),
  };
}

function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = reader.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function drawImageToCanvas(img, canvas, width, height) {
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(img, 0, 0, width, height);
}

function getImageData(canvas) {
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  return ctx.getImageData(0, 0, canvas.width, canvas.height);
}

function putImageData(canvas, imageData) {
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.putImageData(imageData, 0, 0);
}

function cloneImageData(imageData) {
  return new ImageData(
    new Uint8ClampedArray(imageData.data),
    imageData.width,
    imageData.height
  );
}

/** Separable box blur — fast approximation for unsharp mask */
function boxBlur(imageData, radius) {
  if (radius <= 0) return cloneImageData(imageData);

  const { width, height, data } = imageData;
  const out = new Uint8ClampedArray(data.length);
  const tmp = new Float32Array(data.length);
  const r = Math.max(1, Math.round(radius));

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let sumR = 0, sumG = 0, sumB = 0, count = 0;
      for (let dx = -r; dx <= r; dx++) {
        const nx = clamp(x + dx, 0, width - 1);
        const i = (y * width + nx) * 4;
        sumR += data[i];
        sumG += data[i + 1];
        sumB += data[i + 2];
        count++;
      }
      const o = (y * width + x) * 4;
      tmp[o] = sumR / count;
      tmp[o + 1] = sumG / count;
      tmp[o + 2] = sumB / count;
      tmp[o + 3] = data[o + 3];
    }
  }

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let sumR = 0, sumG = 0, sumB = 0, count = 0;
      for (let dy = -r; dy <= r; dy++) {
        const ny = clamp(y + dy, 0, height - 1);
        const i = (ny * width + x) * 4;
        sumR += tmp[i];
        sumG += tmp[i + 1];
        sumB += tmp[i + 2];
        count++;
      }
      const o = (y * width + x) * 4;
      out[o] = sumR / count;
      out[o + 1] = sumG / count;
      out[o + 2] = sumB / count;
      out[o + 3] = data[o + 3];
    }
  }

  return new ImageData(out, width, height);
}

function applyBrightnessContrast(imageData, brightness, contrast) {
  const data = imageData.data;
  const b = brightness * 2.55;
  const factor = (259 * (contrast + 255)) / (255 * (259 - contrast));

  for (let i = 0; i < data.length; i += 4) {
    let r = data[i] + b;
    let g = data[i + 1] + b;
    let bl = data[i + 2] + b;

    r = factor * (r - 128) + 128;
    g = factor * (g - 128) + 128;
    bl = factor * (bl - 128) + 128;

    data[i] = clamp(Math.round(r), 0, 255);
    data[i + 1] = clamp(Math.round(g), 0, 255);
    data[i + 2] = clamp(Math.round(bl), 0, 255);
  }

  return imageData;
}

function applyUnsharpMask(imageData, amount, radius) {
  if (amount <= 0) return imageData;

  const blurred = boxBlur(imageData, radius);
  const src = imageData.data;
  const blur = blurred.data;
  const strength = amount / 50;

  for (let i = 0; i < src.length; i += 4) {
    const dr = src[i] - blur[i];
    const dg = src[i + 1] - blur[i + 1];
    const db = src[i + 2] - blur[i + 2];

    src[i] = clamp(Math.round(src[i] + dr * strength), 0, 255);
    src[i + 1] = clamp(Math.round(src[i + 1] + dg * strength), 0, 255);
    src[i + 2] = clamp(Math.round(src[i + 2] + db * strength), 0, 255);
  }

  return imageData;
}

function applyClarity(imageData, amount) {
  if (amount <= 0) return imageData;

  const blurred = boxBlur(imageData, 8);
  const src = imageData.data;
  const blur = blurred.data;
  const strength = amount / 100;

  for (let i = 0; i < src.length; i += 4) {
    const lum = 0.299 * src[i] + 0.587 * src[i + 1] + 0.114 * src[i + 2];
    const lumBlur = 0.299 * blur[i] + 0.587 * blur[i + 1] + 0.114 * blur[i + 2];
    const midWeight = 1 - Math.abs(lum - 128) / 128;
    const delta = (lum - lumBlur) * strength * midWeight * 2;

    src[i] = clamp(Math.round(src[i] + delta), 0, 255);
    src[i + 1] = clamp(Math.round(src[i + 1] + delta), 0, 255);
    src[i + 2] = clamp(Math.round(src[i + 2] + delta), 0, 255);
  }

  return imageData;
}

function applyDenoise(imageData, amount) {
  if (amount <= 0) return imageData;

  const blurred = boxBlur(imageData, 2);
  const src = imageData.data;
  const blur = blurred.data;
  const threshold = 8 + amount * 0.3;
  const blend = amount / 100;

  for (let i = 0; i < src.length; i += 4) {
    const dr = src[i] - blur[i];
    const dg = src[i + 1] - blur[i + 1];
    const db = src[i + 2] - blur[i + 2];
    const diff = Math.sqrt(dr * dr + dg * dg + db * db);

    if (diff < threshold) {
      src[i] = Math.round(src[i] * (1 - blend) + blur[i] * blend);
      src[i + 1] = Math.round(src[i + 1] * (1 - blend) + blur[i + 1] * blend);
      src[i + 2] = Math.round(src[i + 2] * (1 - blend) + blur[i + 2] * blend);
    }
  }

  return imageData;
}

function upscaleImageData(imageData, percent) {
  if (percent <= 0) return imageData;

  const scale = 1 + percent / 100;
  const newW = Math.round(imageData.width * scale);
  const newH = Math.round(imageData.height * scale);

  const srcCanvas = document.createElement('canvas');
  srcCanvas.width = imageData.width;
  srcCanvas.height = imageData.height;
  putImageData(srcCanvas, imageData);

  const destCanvas = document.createElement('canvas');
  destCanvas.width = newW;
  destCanvas.height = newH;
  const ctx = destCanvas.getContext('2d');
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(srcCanvas, 0, 0, newW, newH);

  return getImageData(destCanvas);
}

function processImageData(sourceData, settings) {
  let data = cloneImageData(sourceData);

  const contrastVal = settings.contrast * 1.2;
  const brightnessVal = settings.brightness;

  if (brightnessVal !== 0 || contrastVal !== 0) {
    data = applyBrightnessContrast(data, brightnessVal, contrastVal);
  }

  if (settings.denoise > 0) {
    data = applyDenoise(data, settings.denoise);
  }

  if (settings.clarity > 0) {
    data = applyClarity(data, settings.clarity);
  }

  const radius = 1 + settings.sharpness / 25;
  if (settings.sharpness > 0) {
    data = applyUnsharpMask(data, settings.sharpness, radius);
  }

  if (settings.upscale > 0) {
    data = upscaleImageData(data, settings.upscale);
  }

  return data;
}

function setProcessing(active) {
  state.processing = active;
  els.processingOverlay.classList.toggle('visible', active);
  els.btnDownload.disabled = active;
}

function updateSliderUI() {
  Object.keys(els.sliders).forEach((key) => {
    const val = state.settings[key];
    els.sliders[key].value = val;
    els.values[key].textContent = formatSliderValue(key, val);
  });
}

function formatSliderValue(key, val) {
  if (key === 'brightness') return val > 0 ? `+${val}` : String(val);
  if (key === 'upscale') return `${val}%`;
  return String(val);
}

function applyPreset(name) {
  state.preset = name;
  const preset = PRESETS[name];
  if (!preset) return;

  Object.assign(state.settings, preset);
  updateSliderUI();

  els.presetBtns.forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.preset === name);
  });
}

function updateComparePosition(percent) {
  state.comparePosition = clamp(percent, 0, 100);
  els.compareAfter.style.clipPath = `inset(0 ${100 - state.comparePosition}% 0 0)`;
  els.compareHandle.style.left = `${state.comparePosition}%`;
}

async function processAndRender() {
  if (!state.originalImage || state.processing) return;

  setProcessing(true);

  await new Promise((r) => setTimeout(r, 10));

  try {
    const sourceData = getImageData(els.beforeCanvas);
    const result = processImageData(sourceData, state.settings);

    els.afterCanvas.width = result.width;
    els.afterCanvas.height = result.height;
    putImageData(els.afterCanvas, result);

    els.compareContainer.style.aspectRatio = `${result.width} / ${result.height}`;
  } finally {
    setProcessing(false);
  }
}

let processTimeout = null;

function scheduleProcess() {
  clearTimeout(processTimeout);
  processTimeout = setTimeout(processAndRender, 120);
}

async function handleFile(file) {
  if (!file || !file.type.startsWith('image/')) {
    alert('Pilih file gambar (JPG, PNG, WebP, dll).');
    return;
  }

  setProcessing(true);

  try {
    const img = await loadImageFromFile(file);
    const dims = scaleDimensions(img.naturalWidth, img.naturalHeight);

    state.originalImage = img;
    state.originalWidth = dims.width;
    state.originalHeight = dims.height;

    drawImageToCanvas(img, els.beforeCanvas, dims.width, dims.height);
    els.afterCanvas.width = dims.width;
    els.afterCanvas.height = dims.height;

    els.uploadZone.classList.add('hidden');
    els.workspace.classList.add('active');
    els.compareContainer.style.aspectRatio = `${dims.width} / ${dims.height}`;

    applyPreset('auto');
    updateComparePosition(50);
    await processAndRender();
  } catch {
    alert('Gagal membuka gambar. Coba file lain.');
  } finally {
    setProcessing(false);
  }
}

function downloadResult() {
  const link = document.createElement('a');
  const timestamp = new Date().toISOString().slice(0, 10);
  link.download = `foto-jelas-${timestamp}.png`;
  link.href = els.afterCanvas.toDataURL('image/png');
  link.click();
}

function resetSettings() {
  applyPreset(state.preset);
  scheduleProcess();
}

function resetApp() {
  state.originalImage = null;
  els.workspace.classList.remove('active');
  els.uploadZone.classList.remove('hidden');
  els.fileInput.value = '';
}

function initCompareSlider() {
  let dragging = false;

  const onMove = (clientX) => {
    if (!dragging) return;
    const rect = els.compareContainer.getBoundingClientRect();
    const percent = ((clientX - rect.left) / rect.width) * 100;
    updateComparePosition(percent);
  };

  const start = () => { dragging = true; };

  const end = () => { dragging = false; };

  els.compareHandle.addEventListener('mousedown', start);
  els.compareContainer.addEventListener('mousedown', (e) => {
    dragging = true;
    onMove(e.clientX);
  });

  document.addEventListener('mousemove', (e) => onMove(e.clientX));
  document.addEventListener('mouseup', end);

  els.compareHandle.addEventListener('touchstart', (e) => {
    e.preventDefault();
    dragging = true;
  }, { passive: false });

  els.compareContainer.addEventListener('touchstart', (e) => {
    dragging = true;
    onMove(e.touches[0].clientX);
  });

  document.addEventListener('touchmove', (e) => {
    if (dragging) onMove(e.touches[0].clientX);
  }, { passive: true });

  document.addEventListener('touchend', end);
}

function initUpload() {
  els.uploadZone.addEventListener('click', () => els.fileInput.click());

  els.fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) handleFile(file);
  });

  els.uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    els.uploadZone.classList.add('dragover');
  });

  els.uploadZone.addEventListener('dragleave', () => {
    els.uploadZone.classList.remove('dragover');
  });

  els.uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    els.uploadZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });
}

function initControls() {
  Object.keys(els.sliders).forEach((key) => {
    els.sliders[key].addEventListener('input', (e) => {
      state.settings[key] = Number(e.target.value);
      els.values[key].textContent = formatSliderValue(key, state.settings[key]);
      state.preset = 'custom';
      els.presetBtns.forEach((btn) => btn.classList.remove('active'));
      scheduleProcess();
    });
  });

  els.presetBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      applyPreset(btn.dataset.preset);
      scheduleProcess();
    });
  });

  els.btnDownload.addEventListener('click', downloadResult);
  els.btnReset.addEventListener('click', resetSettings);
  els.btnNew.addEventListener('click', resetApp);
}

initUpload();
initControls();
initCompareSlider();
updateSliderUI();
