/* Foto Jelas Pro v2 web preview — enhance / colorize / full restore via Replicate */
function el(id) { return document.getElementById(id); }
const state = { mode: 'enhance', beforeURL: null, beforeBlob: null, afterURL: null, busy: false };
const DESCS = {
  enhance: 'Foto buram / low-res jadi tajam natural (CodeFormer + ESRGAN).',
  colorize: 'Foto lama hitam-putih jadi berwarna (DDColor).',
  full: 'Foto lama hitam-putih + buram jadi berwarna tajam (DDColor lalu CodeFormer).'
};
const DEF = { mEnh: 'sczhou/codeformer', mCol: 'piddnad/ddcolor', mUps: 'nightmareai/real-esrgan' };

function loadCfg() {
  el('token').value = localStorage.getItem('fj2.token') || '';
  el('mEnh').value = localStorage.getItem('fj2.mEnh') || DEF.mEnh;
  el('mCol').value = localStorage.getItem('fj2.mCol') || DEF.mCol;
  el('mUps').value = localStorage.getItem('fj2.mUps') || DEF.mUps;
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

async function replicateRun(model, input, label, onp) {
  const token = el('token').value.trim() || localStorage.getItem('fj2.token') || '';
  if (!token) throw new Error('need-token');
  if (onp) onp(5, label + ': antre...');
  let r;
  try {
    r = await fetch('https://api.replicate.com/v1/models/' + model + '/predictions', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: input })
    });
  } catch (netErr) {
    throw new Error('Jaringan/CORS: browser gagal menghubungi api.replicate.com (' + netErr.message + '). Coba refresh, ganti browser/HP, atau kabari saya agar saya pasang backend proxy.');
  }
  if (!r.ok) {
    const t = await r.text();
    let hint = '';
    if (r.status === 401) hint = ' — token salah/kedaluwarsa. Ambil ulang di replicate.com/account/api-tokens lalu Simpan.';
    else if (r.status === 402) hint = ' — kredit habis. Cek billing Replicate.';
    else if (r.status === 422) hint = ' — input tidak cocok untuk model ini. Screenshot pesan ini untuk saya.';
    throw new Error('Replicate ' + r.status + hint + ' Detail: ' + t.slice(0, 500));
  }
  let p = await r.json();
  const t0 = Date.now();
  while (p.status === 'starting' || p.status === 'processing') {
    if (Date.now() - t0 > 5 * 60 * 1000) throw new Error('Timeout 5 menit.');
    await new Promise(function (x) { setTimeout(x, 2500); });
    if (onp) onp(40, label + ': ' + p.status + '...');
    const g = await fetch('https://api.replicate.com/v1/predictions/' + p.id, {
      headers: { Authorization: 'Bearer ' + token }
    }).catch(function (netErr) { throw new Error('Jaringan putus saat menunggu hasil (' + netErr.message + '). Coba lagi.'); });
    p = await g.json();
  }
  if (p.status !== 'succeeded') throw new Error('Gagal: ' + (p.error || p.status));
  const out = Array.isArray(p.output) ? p.output[p.output.length - 1] : p.output;
  return out;
}

async function urlToBlob(u) {
  const r = await fetch(u);
  return await r.blob();
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
  setStatus('Demo selesai. Untuk hasil AI asli isi token Replicate.');
});

el('btnRun').addEventListener('click', async function () {
  if (!state.beforeBlob || state.busy) return;
  state.busy = true;
  setProg(2);
  try {
    const extra = extraJSON();
    const fid = parseFloat(el('fidelity').value);
    const dataURL = await blobToDataURL(state.beforeBlob);
    const onp = function (p, m) { setProg(p); setStatus(m); };
    let curURL = null;
    if (state.mode === 'enhance') {
      const input = Object.assign(
        { image: dataURL, face_upsample: true, background_enhance: true, codeformer_fidelity: fid, upscale: 2 },
        extra
      );
      curURL = await replicateRun(el('mEnh').value.trim() || DEF.mEnh, input, 'Perjelas', onp);
    } else if (state.mode === 'colorize') {
      const input = Object.assign({ image: dataURL }, extra);
      curURL = await replicateRun(el('mCol').value.trim() || DEF.mCol, input, 'Warnai', onp);
    } else {
      const inCol = Object.assign({ image: dataURL }, extra.colorize || {});
      curURL = await replicateRun(
        el('mCol').value.trim() || DEF.mCol, inCol, 'Langkah 1/2 warnai',
        function (p) { onp(p / 2, 'Langkah 1/2 warnai...'); }
      );
      const inEnh = Object.assign(
        { image: curURL, face_upsample: true, background_enhance: true, codeformer_fidelity: fid, upscale: 2 },
        extra.enhance || {}
      );
      curURL = await replicateRun(
        el('mEnh').value.trim() || DEF.mEnh, inEnh, 'Langkah 2/2 tajamkan',
        function (p) { onp(50 + p / 2, 'Langkah 2/2 tajamkan...'); }
      );
    }
    onp(92, 'Unduh hasil...');
    const blob = await urlToBlob(curURL);
    showResult(blob);
    onp(100, 'Selesai.');
  } catch (e) {
    if (String(e.message) === 'need-token') {
      alert('Isi API token Replicate dulu (gratis trial), atau pakai Coba tanpa token untuk demo.');
      setStatus('Butuh token.');
    } else {
      console.error(e);
      alert(e.message);
      setStatus('Error: ' + e.message);
    }
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
