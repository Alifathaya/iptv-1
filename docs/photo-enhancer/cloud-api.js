/**
 * Cloud GPU API client for Foto Jelas Pro backend
 */

const STORAGE_URL = 'fotojelas.cloudApiUrl';
const STORAGE_KEY = 'fotojelas.cloudApiKey';

export function getCloudApiUrl() {
  return (localStorage.getItem(STORAGE_URL) || '').replace(/\/$/, '');
}

export function getCloudApiKey() {
  return localStorage.getItem(STORAGE_KEY) || '';
}

export function setCloudSettings(url, key) {
  localStorage.setItem(STORAGE_URL, url.replace(/\/$/, ''));
  localStorage.setItem(STORAGE_KEY, key);
}

export function hasCloudConfigured() {
  return getCloudApiUrl().length > 0;
}

function headers() {
  const h = {};
  const key = getCloudApiKey();
  if (key) h['X-API-Key'] = key;
  return h;
}

export async function checkCloudHealth() {
  const base = getCloudApiUrl();
  if (!base) throw new Error('URL API belum diatur');

  const res = await fetch(`${base}/health`, { method: 'GET' });
  if (!res.ok) throw new Error(`Server error ${res.status}`);
  return res.json();
}

export async function enhanceViaCloud(blob, options, onProgress) {
  const base = getCloudApiUrl();
  if (!base) throw new Error('URL API GPU belum diatur. Buka pengaturan Cloud GPU.');

  const form = new FormData();
  form.append('image', blob, 'photo.png');
  form.append('scale', String(options.scale || 4));
  form.append('deblur', String(options.deblur ?? 80));
  form.append('sharpness', String(options.sharpness ?? 60));
  form.append('contrast', String(options.contrast ?? 25));

  onProgress?.(15, 'Mengunggah ke server GPU…');

  const res = await fetch(`${base}/v1/enhance`, {
    method: 'POST',
    headers: headers(),
    body: form,
  });

  if (!res.ok) {
    let detail = `Server error ${res.status}`;
    try {
      const err = await res.json();
      if (err.detail) detail = err.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  onProgress?.(75, 'GPU memproses Real-ESRGAN…');

  const resultBlob = await res.blob();
  onProgress?.(95, 'Menerima hasil dari GPU…');

  return resultBlob;
}

export function blobToImageData(blob) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);
      const data = ctx.getImageData(0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      resolve(data);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Gagal membaca hasil gambar'));
    };
    img.src = url;
  });
}

export async function canvasToBlob(canvas, type = 'image/png') {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error('Gagal membuat blob'));
    }, type, 0.95);
  });
}
