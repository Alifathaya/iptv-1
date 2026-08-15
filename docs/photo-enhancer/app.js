/**
 * Foto Jelas Pro — AI-enhanced photo sharpening & deblur
 */

import { fitMaxDimension, scaleImageData } from './filters.js';

const AI_INPUT_MAX = 480;
const UPSCALER_URL = 'https://esm.sh/upscaler@1.0.0-beta.19';
const ESRGAN_X4_URL = 'https://esm.sh/@upscalerjs/esrgan-thick@1.0.0-beta.14/x4';

const state = {
  originalImage: null,
  mode: 'extreme',
  settings: {
    sharpness: 60,
    clarity: 50,
    contrast: 25,
    brightness: 0,
    denoise: 25,
    deblur: 80,
    upscale: 0,
  },
  preset: 'extreme',
  comparePosition: 50,
  processing: false,
  aiReady: false,
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
  modeBtns: document.querySelectorAll('.mode-btn'),
  presetBtns: document.querySelectorAll('.preset-btn'),
  sliders: {
    sharpness: document.getElementById('sharpness'),
    clarity: document.getElementById('clarity'),
    contrast: document.getElementById('contrast'),
    brightness: document.getElementById('brightness'),
    denoise: document.getElementById('denoise'),
    deblur: document.getElementById('deblur'),
  },
  values: {
    sharpness: document.getElementById('sharpnessValue'),
    clarity: document.getElementById('clarityValue'),
    contrast: document.getElementById('contrastValue'),
    brightness: document.getElementById('brightnessValue'),
    denoise: document.getElementById('denoiseValue'),
    deblur: document.getElementById('deblurValue'),
  },
  deblurGroup: document.getElementById('deblurGroup'),
  btnDownload: document.getElementById('btnDownload'),
  btnReset: document.getElementById('btnReset'),
  btnNew: document.getElementById('btnNew'),
  btnEnhance: document.getElementById('btnEnhance'),
  processingOverlay: document.getElementById('processingOverlay'),
  progressBar: document.getElementById('progressBar'),
  progressText: document.getElementById('progressText'),
  progressStep: document.getElementById('progressStep'),
  aiBadge: document.getElementById('aiBadge'),
};

const PRESETS = {
  extreme: { mode: 'extreme', sharpness: 70, clarity: 55, contrast: 30, brightness: 5, denoise: 30, deblur: 85, upscale: 0 },
  blur: { mode: 'pro', sharpness: 75, clarity: 55, contrast: 25, brightness: 5, denoise: 30, deblur: 70, upscale: 0 },
  document: { mode: 'pro', sharpness: 90, clarity: 35, contrast: 50, brightness: 10, denoise: 15, deblur: 60, upscale: 0 },
  portrait: { mode: 'pro', sharpness: 45, clarity: 40, contrast: 15, brightness: 5, denoise: 40, deblur: 40, upscale: 0 },
  auto: { mode: 'fast', sharpness: 50, clarity: 40, contrast: 20, brightness: 0, denoise: 15, deblur: 0, upscale: 0 },
};

let worker = new Worker('./processor.worker.js', { type: 'module' });
let upscalerInstance = null;
let processTimeout = null;

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function scaleDimensions(width, height) {
  const maxSide = Math.max(width, height);
  const maxDim = 2048;
  if (maxSide <= maxDim) return { width, height };
  const scale = maxDim / maxSide;
  return { width: Math.round(width * scale), height: Math.round(height * scale) };
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
  ctx.fillStyle = '#050508';
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

function imageDataToCanvas(imageData) {
  const canvas = document.createElement('canvas');
  canvas.width = imageData.width;
  canvas.height = imageData.height;
  putImageData(canvas, imageData);
  return canvas;
}

function canvasToImage(canvas) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = canvas.toDataURL('image/png');
  });
}

function imageElementToImageData(img) {
  const canvas = document.createElement('canvas');
  canvas.width = img.naturalWidth || img.width;
  canvas.height = img.naturalHeight || img.height;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0);
  return ctx.getImageData(0, 0, canvas.width, canvas.height);
}

function updateProgress(pct, message) {
  const p = clamp(pct, 0, 100);
  els.progressBar.style.width = `${p}%`;
  els.progressText.textContent = `${Math.round(p)}%`;
  if (message) els.progressStep.textContent = message;
}

function setProcessing(active) {
  state.processing = active;
  els.processingOverlay.classList.toggle('visible', active);
  els.btnDownload.disabled = active;
  els.btnEnhance.disabled = active;
  if (!active) {
    updateProgress(0, '');
  }
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
  return String(val);
}

function setMode(mode) {
  state.mode = mode;
  els.modeBtns.forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });
  els.deblurGroup.style.display = mode === 'fast' ? 'none' : 'block';
  els.aiBadge.classList.toggle('visible', mode === 'extreme');
}

function applyPreset(name) {
  state.preset = name;
  const preset = PRESETS[name];
  if (!preset) return;

  setMode(preset.mode);
  Object.assign(state.settings, {
    sharpness: preset.sharpness,
    clarity: preset.clarity,
    contrast: preset.contrast,
    brightness: preset.brightness,
    denoise: preset.denoise,
    deblur: preset.deblur,
    upscale: preset.upscale ?? 0,
  });
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

function runWorker(task, imageData, workerMode) {
  return new Promise((resolve, reject) => {
    const clone = new ImageData(
      new Uint8ClampedArray(imageData.data),
      imageData.width,
      imageData.height
    );

    const handler = (e) => {
      const msg = e.data;
      if (msg.type === 'progress') {
        updateProgress(msg.pct, msg.message);
      } else if (msg.type === 'done' && msg.mode === workerMode) {
        worker.removeEventListener('message', handler);
        resolve(msg.imageData);
      } else if (msg.type === 'error') {
        worker.removeEventListener('message', handler);
        reject(new Error(msg.message));
      }
    };

    worker.addEventListener('message', handler);
    worker.postMessage(
      { task, imageData: clone, settings: state.settings, mode: workerMode },
      [clone.data.buffer]
    );
  });
}

async function loadUpscaler() {
  if (upscalerInstance) return upscalerInstance;

  updateProgress(5, 'Mengunduh model AI ESRGAN…');

  const { default: Upscaler } = await import(UPSCALER_URL);
  const { default: x4 } = await import(ESRGAN_X4_URL);

  upscalerInstance = new Upscaler({
    model: x4,
  });

  state.aiReady = true;
  return upscalerInstance;
}

async function aiUpscale4x(imageData) {
  const upscaler = await loadUpscaler();
  const work = fitMaxDimension(imageData, AI_INPUT_MAX);
  const canvas = imageDataToCanvas(work);
  const img = await canvasToImage(canvas);

  updateProgress(40, 'Neural network membangun detail 4x…');

  const upscaled = await upscaler.upscale(img, {
    progress: (pct) => {
      const normalized = pct <= 1 ? pct : pct / 100;
      updateProgress(40 + normalized * 45, 'AI Super Resolution 4x…');
    },
  });

  if (upscaled instanceof HTMLImageElement) {
    return imageElementToImageData(upscaled);
  }

  if (upscaled instanceof HTMLCanvasElement) {
    return getImageData(upscaled);
  }

  throw new Error('Format hasil AI tidak dikenali');
}

async function processAndRender() {
  if (!state.originalImage || state.processing) return;

  setProcessing(true);
  updateProgress(2, 'Memulai…');

  try {
    const sourceData = getImageData(els.beforeCanvas);
    let result;

    if (state.mode === 'fast') {
      result = await runWorker('process', sourceData, 'fast');
    } else if (state.mode === 'pro') {
      result = await runWorker('process', sourceData, 'pro');
    } else if (state.mode === 'extreme') {
      updateProgress(8, 'Deblur ekstrem (Richardson-Lucy)…');
      const prepped = await runWorker('process', sourceData, 'pre-extreme');

      try {
        result = await aiUpscale4x(prepped);
      } catch (aiErr) {
        console.warn('AI upscale failed, using algorithmic fallback:', aiErr);
        updateProgress(50, 'AI gagal — upscale algoritmik 2x…');
        const fallback = scaleImageData(prepped, prepped.width * 2, prepped.height * 2);
        result = await runWorker('process', fallback, 'post-polish');
      }

      updateProgress(88, 'Polish akhir…');
      result = await runWorker('process', result, 'post-polish');
    }

    els.afterCanvas.width = result.width;
    els.afterCanvas.height = result.height;
    putImageData(els.afterCanvas, result);
    els.compareContainer.style.aspectRatio = `${result.width} / ${result.height}`;
    updateProgress(100, 'Selesai!');
  } catch (err) {
    console.error(err);
    alert('Gagal memproses foto. Coba foto lebih kecil atau mode Cepat.');
  } finally {
    setTimeout(() => setProcessing(false), 400);
  }
}

function scheduleProcess() {
  clearTimeout(processTimeout);
  processTimeout = setTimeout(processAndRender, 200);
}

async function handleFile(file) {
  if (!file || !file.type.startsWith('image/')) {
    alert('Pilih file gambar (JPG, PNG, WebP, dll).');
    return;
  }

  setProcessing(true);
  updateProgress(0, 'Membuka foto…');

  try {
    const img = await loadImageFromFile(file);
    const dims = scaleDimensions(img.naturalWidth, img.naturalHeight);

    state.originalImage = img;

    drawImageToCanvas(img, els.beforeCanvas, dims.width, dims.height);
    els.afterCanvas.width = dims.width;
    els.afterCanvas.height = dims.height;

    els.uploadZone.classList.add('hidden');
    els.workspace.classList.add('active');
    els.compareContainer.style.aspectRatio = `${dims.width} / ${dims.height}`;

    applyPreset('extreme');
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
  link.download = `foto-jelas-pro-${timestamp}.png`;
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
    updateComparePosition(((clientX - rect.left) / rect.width) * 100);
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
      if (state.mode !== 'extreme') scheduleProcess();
    });
  });

  els.presetBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      applyPreset(btn.dataset.preset);
      scheduleProcess();
    });
  });

  els.modeBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      setMode(btn.dataset.mode);
      state.preset = 'custom';
      els.presetBtns.forEach((b) => b.classList.remove('active'));
      scheduleProcess();
    });
  });

  els.btnDownload.addEventListener('click', downloadResult);
  els.btnReset.addEventListener('click', resetSettings);
  els.btnNew.addEventListener('click', resetApp);
  els.btnEnhance.addEventListener('click', () => processAndRender());
}

initUpload();
initControls();
initCompareSlider();
setMode('extreme');
updateSliderUI();

// Pre-warm AI model hint on idle
if ('requestIdleCallback' in window) {
  requestIdleCallback(() => {
    loadUpscaler().catch(() => {});
  }, { timeout: 8000 });
}
