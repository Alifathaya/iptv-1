/* Foto Jelas Pro v2 web preview — enhance / colorize / full restore via fal.ai */
function el(id) { return document.getElementById(id); }
const state = { mode: 'enhance', beforeURL: null, beforeBlob: null, afterURL: null, busy: false };
const DESCS = {
  enhance: 'Foto buram / low-res jadi tajam natural (CodeFormer + ESRGAN).',
  colorize: 'Foto lama hitam-putih jadi berwarna (DDColor).',
  full: 'Foto lama hitam-putih + buram jadi berwarna tajam (DDColor lalu CodeFormer).'
};
const DEF = { mEnh: 'fal-ai/codeformer', mCol: 'fal-ai/ddcolor' };

function loadCfg() {
  el('token').value = localStorage.getItem('fj2.token') || '';
  el('mEnh').value = localStorage.getItem('fj2.mEnh') || DEF.mEnh;
  el('mCol').value = localStorage.getItem('fj2.mCol') || DEF.mCol;
  el('mUps').value = localStorage.getItem('fj2.mUps') || '2';
}
function setStatus(m) { el('status').textContent = m || ''; }
function setProg(p) {
  el('prog').classList.remove('hidden');
  el('bar').style.width = Math.round(p) + '%';
}
function doneProg() { setTimeout(function () { el('prog').classList.add('hidden'); }, 600); }

document.querySelectorAll('.tab').forEach(function (b) {
  b.addEventListener('click', function () {
    document.querySelectorAll('.tab').forEach(function (x) { x.classList.remove('active'); });
    b.classList.add('active');
    state.mode = b.dataset.mode;
    el('modeDesc').textContent = DESCS[state.mode];
    el('btnRun').textContent = state.mode === 'colorize' ? 'Warnai' : state.mode === 'full' ? 'Full Restore' : 'Enhance';
  });
});
el('fidelity').addEventListener('input', function (e) { el('fidVal').textContent = e.target.value; });
el('btnPick').addEventListener('click', function () { el('fileInput').click(); });
el('btnReset').addEventListener('click', function () {
  el('work').classList.add('hidden');
  el('dropZone').classList.remove('hidden');
  el('fileInput').value = '';
  setStatus('');
});
el('btnSave').addEventListener('click', function () {
  localStorage.setItem('fj2.token', el('token').value.trim());
  localStorage.setItem('fj2.mEnh', el('mEnh').value.trim() || DEF.mEnh);
  localStorage.setItem('fj2.mCol', el('mCol').value.trim() || DEF.mCol);
  localStorage.setItem('fj2.mUps', el('mUps').value.trim() || DEF.mUps);
  setStatus('Pengaturan tersimpan di browser ini.');
});

el('fileInput').addEventListener('change', async function (e) {
  const f = e.target.files[0];
  if (!f) return;
  if (f.size > 10 * 1024 * 1024) { alert('Maks 10MB.'); return; }
  const bmp = await createImageBitmap(f);
  const maxSide = 2048, s = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const w = Math.round(bmp.width * s), h = Math.round(bmp.height * s);
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  c.getContext('2d').drawImage(bmp, 0, 0, w, h);
  const blob = await new Promise(function (r) {
    if (c.convertToBlob) c.convertToBlob(r, 'image/jpeg', 0.92);
    else c.toBlob(r, 'image/jpeg', 0.92);
  });
  state.beforeBlob = blob;
  if (state.beforeURL) URL.revokeObjectURL(state.beforeURL);
  state.beforeURL = URL.createObjectURL(blob);
  el('imgBefore').src = state.beforeURL;
  el('imgAfter').src = state.beforeURL;
  el('imgAfter').style.clipPath = 'inset(0 50% 0 0)';
  el('handle').style.left = '50%';
  el('btnDl').classList.add('hidden');
  el('dropZone').classList.add('hidden');
  el('work').classList.remove('hidden');
  setStatus('Siap. Pilih mode lalu tekan ' + el('btnRun').textContent + '.');
});

// compare slider
(function () {
  const cmp = el('compare');
  let drag = false;
  function move(ev) {
    const r = cmp.getBoundingClientRect();
    const cx = ev.touches ? ev.touches[0].clientX : ev.clientX;
    const p = Math.max(0, Math.min(100, ((cx - r.left) / r.width) * 100));
    el('imgAfter').style.clipPath = 'inset(0 ' + (100 - p) + '% 0 0)';
    el('handle').style.left = p + '%';
  }
  cmp.addEventListener('pointerdown', function (e) { drag = true; move(e); });
  window.addEventListener('pointermove', function (e) { if (drag) move(e); });
  window.addEventListener('pointerup', function () { drag = false; });
})();

function extraJSON() {
  try {
    return JSON.parse(el('extra').value.trim() || '{}');
  } catch (err) {
    alert('JSON tambahan tidak valid.');
    throw new Error('bad json');
  }
}

function blobToDataURL(blob) {
  return new Promise(function (res, rej) {
    const fr = new FileReader();
    fr.onload = function () { res(fr.result); };
    fr.onerror = rej;
    fr.readAsDataURL(blob);
  });
}

async function b64ToBlob(b64) {
  const res = await fetch(b64);
  return await res.blob();
}

async function urlToBlob(u) {
  const r = await fetch(u);
  return await r.blob();
}

// Semua panggilan fal.ai lewat proxy VPS (same-origin) agar bebas CORS.
// Key dikirim per-request via header, tidak disimpan di server.
async function runViaProxy(body, token, onp) {
  const ctrl = new AbortController();
  const t = setTimeout(function () { ctrl.abort(); }, 8 * 60 * 1000);
  // progress palsu selama server bekerja (poll asli ada di server)
  let p = 5;
  const tick = setInterval(function () {
    p = Math.min(90, p + 2);
    if (onp) onp(p, 'AI bekerja di server...');
  }, 3000);
  try {
    const r = await fetch('/api/restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Fal-Key': token },
      body: JSON.stringify(body),
      signal: ctrl.signal
    });
    if (!r.ok) {
      let detail = '';
      try { detail = (await r.json()).detail || ''; } catch (e) { detail = await r.text(); }
      let hint = '';
      if (r.status === 400 && String(detail).indexOf('Key') >= 0) hint = 'Isi API key fal.ai dulu lalu Simpan.';
      throw new Error('Server ' + r.status + (hint ? ' — ' + hint : '') + ' ' + String(detail).slice(0, 500));
    }
    const j = await r.json();
    if (onp) onp(92, 'Unduh hasil...');
    if (j.image_b64) return await b64ToBlob(j.image_b64);
    return await urlToBlob(j.image_url);
  } catch (e) {
    if (e.name === 'AbortError') throw new Error('Timeout 8 menit. Coba foto lebih kecil.');
    throw e;
  } finally {
    clearTimeout(t);
    clearInterval(tick);
  }
}

// demo lokal: kontras ringan agar UI bisa dicek tanpa token
async function demoLocal() {
  const img = new Image();
  img.src = state.beforeURL;
  await img.decode();
  const c = document.createElement('canvas');
  c.width = img.naturalWidth;
  c.height = img.naturalHeight;
  const x = c.getContext('2d');
  x.drawImage(img, 0, 0);
  const d = x.getImageData(0, 0, c.width, c.height), s = d.data;
  for (let i = 0; i < s.length; i += 4) {
    for (let k = 0; k < 3; k++) {
      s[i + k] = Math.max(0, Math.min(255, (s[i + k] - 128) * 1.15 + 128));
    }
  }
  x.putImageData(d, 0, 0);
  return new Promise(function (r) { c.toBlob(r, 'image/png'); });
}

el('btnDemo').addEventListener('click', async function () {
  if (!state.beforeBlob) { alert('Pilih foto dulu.'); return; }
  setProg(50);
  setStatus('Demo lokal (bukan AI)...');
  const b = await demoLocal();
  showResult(b);
  setProg(100);
  doneProg();
  setStatus('Demo selesai. Untuk hasil AI asli isi key fal.ai.');
});

el('btnRun').addEventListener('click', async function () {
  if (!state.beforeBlob || state.busy) return;
  state.busy = true;
  setProg(2);
  try {
    const token = el('token').value.trim() || localStorage.getItem('fj2.token') || '';
    if (!token) {
      alert('Isi API key fal.ai dulu (gratis $10), atau pakai Coba tanpa token untuk demo.');
      setStatus('Butuh key.');
      return;
    }
    const extra = extraJSON();
    const fid = parseFloat(el('fidelity').value);
    const ups = parseInt(el('mUps').value.trim() || '2', 10) || 2;
    const dataURL = await blobToDataURL(state.beforeBlob);
    const onp = function (p, m) { setProg(p); setStatus(m); };
    onp(3, state.mode === 'colorize' ? 'Mewarnai...' : state.mode === 'full' ? 'Full restore...' : 'Memperjelas...');
    const blob = await runViaProxy({
      mode: state.mode,
      image: dataURL,
      fidelity: fid,
      upscale: ups,
      model_enhance: el('mEnh').value.trim() || DEF.mEnh,
      model_colorize: el('mCol').value.trim() || DEF.mCol,
      extra: extra
    }, token, onp);
    showResult(blob);
    onp(100, 'Selesai.');
  } catch (e) {
    console.error(e);
    alert(e.message);
    setStatus('Error: ' + e.message);
  } finally {
    state.busy = false;
    doneProg();
  }
});

function showResult(blob) {
  if (state.afterURL) URL.revokeObjectURL(state.afterURL);
  state.afterURL = URL.createObjectURL(blob);
  el('imgAfter').src = state.afterURL;
  const a = el('btnDl');
  a.href = state.afterURL;
  a.classList.remove('hidden');
}

loadCfg();
