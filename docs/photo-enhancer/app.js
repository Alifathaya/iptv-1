/**
 * Foto Jelas Pro — AI-enhanced photo sharpening & deblur
 */

import { fitMaxDimension, scaleImageData } from './filters.js';
import { isNativeApp, saveAndShareImage, saveToDocuments } from './native.js';
import {
  blobToImageData,
  canvasToBlob,
  checkCloudHealth,
  enhanceViaCloud,
  getCloudApiKey,
  getCloudApiUrl,
  hasCloudConfigured,
  setCloudSettings,
} from './cloud-api.js';

const AI_INPUT_MAX = 480;
const AI_INPUT_ULTRA = 320;
const UPSCALER_URL = 'https://esm.sh/upscaler@1.0.0-beta.19';
const ESRGAN_X4_URL = 'https://esm.sh/@upscalerjs/esrgan-thick@1.0.0-beta.14/x4';
const ESRGAN_X8_URL = 'https://esm.sh/@upscalerjs/esrgan-thick@1.0.0-beta.14/x8';

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
  preset: 'jelas',
  comparePosition: 50,
  processing: false,
  exportImageData: null,
};

let els = {};
let worker;
let upscalerCache = {};
let processTimeout = null;

const PRESETS = {
  jelas: { mode: 'fast', sharpness: 85, clarity: 50, contrast: 45, brightness: 3, denoise: 0, deblur: 0, upscale: 0 },
  cloud: { mode: 'cloud-8', sharpness: 70, clarity: 50, contrast: 35, brightness: 5, denoise: 15, deblur: 30, upscale: 0 },
  ultra: { mode: 'ultra', sharpness: 75, clarity: 50, contrast: 35, brightness: 5, denoise: 20, deblur: 35, upscale: 0 },
  extreme: { mode: 'extreme', sharpness: 70, clarity: 50, contrast: 30, brightness: 5, denoise: 20, deblur: 30, upscale: 0 },
  blur: { mode: 'pro', sharpness: 75, clarity: 50, contrast: 30, brightness: 5, denoise: 25, deblur: 35, upscale: 0 },
  document: { mode: 'pro', sharpness: 85, clarity: 40, contrast: 45, brightness: 10, denoise: 10, deblur: 25, upscale: 0 },
  portrait: { mode: 'pro', sharpness: 50, clarity: 40, contrast: 20, brightness: 5, denoise: 30, deblur: 20, upscale: 0 },
  auto: { mode: 'fast', sharpness: 65, clarity: 45, contrast: 35, brightness: 0, denoise: 0, deblur: 0, upscale: 0 },
};

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function scaleDimensions(width, height) {
  const maxSide = Math.max(width, height);
  const maxDim = 3072;
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
  const ctx = canvas.getContext('2d', { willReadFrequently: true, alpha: false });
  ctx.fillStyle = '#050508';
  ctx.fillRect(0, 0, width, height);
  const downscaling = width < img.naturalWidth || height < img.naturalHeight;
  ctx.imageSmoothingEnabled = downscaling;
  if (downscaling) ctx.imageSmoothingQuality = 'high';
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
  els.btnShare.disabled = active;
  els.btnEnhance.disabled = active;
  if (!active) updateProgress(0, '');
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

function isAiMode(mode = state.mode) {
  return mode === 'extreme' || mode === 'ultra';
}

function isCloudMode(mode = state.mode) {
  return mode === 'cloud-4' || mode === 'cloud-8';
}

function isHeavyMode(mode = state.mode) {
  return isAiMode(mode) || isCloudMode(mode);
}

function setMode(mode) {
  state.mode = mode;
  els.modeBtns.forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });
  els.deblurGroup.style.display = mode === 'fast' ? 'none' : 'block';
  els.cloudSettings.classList.toggle('visible', isCloudMode(mode));

  const showBadge = mode === 'fast' || isAiMode(mode) || isCloudMode(mode);
  els.aiBadge.classList.toggle('visible', showBadge);

  if (mode === 'fast') {
    els.aiBadge.textContent = '✨ Mode Jelas — ketajaman & kontras';
  } else if (isCloudMode(mode)) {
    els.aiBadge.textContent = mode === 'cloud-8'
      ? '☁️ Cloud GPU — Real-ESRGAN 8x'
      : '☁️ Cloud GPU — Real-ESRGAN 4x';
  } else if (mode === 'ultra') {
    els.aiBadge.textContent = 'Mode ULTRA — ESRGAN 8x aktif';
  } else if (mode === 'extreme') {
    els.aiBadge.textContent = 'Mode AI ESRGAN 4x aktif';
  }
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

async function loadUpscaler(scale) {
  const key = `x${scale}`;
  if (upscalerCache[key]) return upscalerCache[key];

  updateProgress(5, `Mengunduh model AI ESRGAN ${scale}x…`);

  const { default: Upscaler } = await import(UPSCALER_URL);
  const modelUrl = scale === 8 ? ESRGAN_X8_URL : ESRGAN_X4_URL;
  const { default: model } = await import(modelUrl);

  upscalerCache[key] = new Upscaler({ model });
  return upscalerCache[key];
}

async function aiUpscale(imageData, scale) {
  const upscaler = await loadUpscaler(scale);
  const maxInput = scale === 8 ? AI_INPUT_ULTRA : AI_INPUT_MAX;
  const work = fitMaxDimension(imageData, maxInput);
  const canvas = imageDataToCanvas(work);
  const img = await canvasToImage(canvas);

  const label = `AI Super Resolution ${scale}x…`;
  updateProgress(40, label);

  const upscaled = await upscaler.upscale(img, {
    progress: (pct) => {
      const normalized = pct <= 1 ? pct : pct / 100;
      updateProgress(40 + normalized * 45, label);
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

async function runAiPipeline(sourceData, scale) {
  updateProgress(8, 'Deblur ekstrem (Richardson-Lucy)…');
  const prepped = await runWorker('process', sourceData, 'pre-extreme');

  let result;
  try {
    result = await aiUpscale(prepped, scale);
  } catch (aiErr) {
    console.warn('AI upscale failed, using algorithmic fallback:', aiErr);
    updateProgress(50, 'AI gagal — upscale algoritmik…');
    const mult = scale === 8 ? 4 : 2;
    const fallback = scaleImageData(prepped, prepped.width * mult, prepped.height * mult);
    result = await runWorker('process', fallback, 'post-polish');
    return result;
  }

  updateProgress(88, 'Polish akhir…');
  return await runWorker('process', result, 'post-polish');
}

async function runCloudPipeline(sourceData, scale) {
  if (!hasCloudConfigured()) {
    els.cloudSettings.classList.add('visible');
    els.cloudSettings.scrollIntoView({ behavior: 'smooth', block: 'center' });
    throw new Error('Atur URL server GPU di pengaturan Cloud GPU.');
  }

  updateProgress(8, 'Menyiapkan foto untuk GPU…');
  const canvas = imageDataToCanvas(sourceData);
  const blob = await canvasToBlob(canvas);

  const resultBlob = await enhanceViaCloud(
    blob,
    {
      scale,
      deblur: state.settings.deblur,
      sharpness: state.settings.sharpness,
      contrast: state.settings.contrast,
    },
    updateProgress,
  );

  return await blobToImageData(resultBlob);
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
      result = await runAiPipeline(sourceData, 4);
    } else if (state.mode === 'ultra') {
      result = await runAiPipeline(sourceData, 8);
    } else if (state.mode === 'cloud-4') {
      result = await runCloudPipeline(sourceData, 4);
    } else if (state.mode === 'cloud-8') {
      result = await runCloudPipeline(sourceData, 8);
    }

    state.exportImageData = result;
    els.afterCanvas.width = result.width;
    els.afterCanvas.height = result.height;
    putImageData(els.afterCanvas, result);
    els.compareContainer.style.aspectRatio = `${result.width} / ${result.height}`;
    updateProgress(100, 'Selesai!');
  } catch (err) {
    console.error(err);
    const msg = err.message || 'Gagal memproses foto.';
    alert(isCloudMode() ? msg : 'Gagal memproses foto. Coba foto lebih kecil atau mode Cepat.');
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

    applyPreset('jelas');
    updateComparePosition(50);
    await processAndRender();
  } catch {
    alert('Gagal membuka gambar. Coba file lain.');
  } finally {
    setProcessing(false);
  }
}

function getResultDataUrl() {
  const data = state.exportImageData;
  if (data) {
    const canvas = imageDataToCanvas(data);
    return canvas.toDataURL('image/png');
  }
  return els.afterCanvas.toDataURL('image/png');
}

async function downloadResult() {
  const dataUrl = getResultDataUrl();

  if (isNativeApp()) {
    try {
      const fileName = await saveToDocuments(dataUrl);
      alert(`Foto disimpan ke Documents/${fileName}`);
    } catch (err) {
      console.error(err);
      alert('Gagal menyimpan. Coba Bagikan.');
    }
    return;
  }

  const link = document.createElement('a');
  const timestamp = new Date().toISOString().slice(0, 10);
  link.download = `foto-jelas-pro-${timestamp}.png`;
  link.href = dataUrl;
  link.click();
}

async function shareResult() {
  const dataUrl = getResultDataUrl();

  if (isNativeApp()) {
    try {
      await saveAndShareImage(dataUrl);
    } catch (err) {
      if (err?.message !== 'Share canceled') {
        console.error(err);
        alert('Gagal membagikan foto.');
      }
    }
    return;
  }

  if (navigator.share && navigator.canShare) {
    try {
      const blob = await (await fetch(dataUrl)).blob();
      const file = new File([blob], 'foto-jelas-pro.png', { type: 'image/png' });
      if (navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: 'Foto Jelas Pro' });
        return;
      }
    } catch (err) {
      if (err?.name === 'AbortError') return;
    }
  }

  downloadResult();
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
      if (!isHeavyMode()) scheduleProcess();
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
  els.btnShare.addEventListener('click', shareResult);
  els.btnReset.addEventListener('click', resetSettings);
  els.btnNew.addEventListener('click', resetApp);
  els.btnEnhance.addEventListener('click', () => processAndRender());

  if (els.btnCloudSave) {
    els.btnCloudSave.addEventListener('click', () => {
      setCloudSettings(els.cloudApiUrl.value.trim(), els.cloudApiKey.value.trim());
      alert('Pengaturan Cloud GPU disimpan.');
    });
  }

  if (els.btnCloudTest) {
    els.btnCloudTest.addEventListener('click', async () => {
      setCloudSettings(els.cloudApiUrl.value.trim(), els.cloudApiKey.value.trim());
      els.btnCloudTest.disabled = true;
      els.cloudStatus.textContent = 'Menghubungkan…';
      try {
        const health = await checkCloudHealth();
        const gpu = health.gpu?.available
          ? `GPU: ${health.gpu.name}`
          : 'CPU mode (tanpa GPU)';
        els.cloudStatus.textContent = `✓ Terhubung — ${gpu}`;
        els.cloudStatus.classList.add('ok');
      } catch (err) {
        els.cloudStatus.textContent = `✗ ${err.message}`;
        els.cloudStatus.classList.remove('ok');
      } finally {
        els.btnCloudTest.disabled = false;
      }
    });
  }
}

function bindElements() {
  els = {
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
    btnShare: document.getElementById('btnShare'),
    btnReset: document.getElementById('btnReset'),
    btnNew: document.getElementById('btnNew'),
    btnEnhance: document.getElementById('btnEnhance'),
    processingOverlay: document.getElementById('processingOverlay'),
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    progressStep: document.getElementById('progressStep'),
    aiBadge: document.getElementById('aiBadge'),
    cloudSettings: document.getElementById('cloudSettings'),
    cloudApiUrl: document.getElementById('cloudApiUrl'),
    cloudApiKey: document.getElementById('cloudApiKey'),
    cloudStatus: document.getElementById('cloudStatus'),
    btnCloudSave: document.getElementById('btnCloudSave'),
    btnCloudTest: document.getElementById('btnCloudTest'),
  };

  if (els.cloudApiUrl) {
    els.cloudApiUrl.value = getCloudApiUrl();
    els.cloudApiKey.value = getCloudApiKey();
  }
}

export function initApp() {
  bindElements();
  worker = new Worker('./processor.worker.js', { type: 'module' });

  initUpload();
  initControls();
  initCompareSlider();
  setMode('fast');
  updateSliderUI();

  if (isNativeApp()) {
    document.body.classList.add('native-app');
  }
}
