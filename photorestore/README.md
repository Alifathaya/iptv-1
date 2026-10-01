# FotoRestore — AI Photo Restoration (Phase 1)

## 1. Arsitektur

```
Android (Kotlin) --HTTPS--> Backend API (FastAPI, Contabo)
                               |  POST /api/v1/enhance -> {job_id, queued}
                               |  GET  /api/v1/jobs/{id} -> progress 0-100
                               v
                         Redis + RQ (Job Queue)
                               v
                         AI Worker (Phase 1: CPU di server yang sama;
                                    Phase 5: pindah ke GPU Vast.ai tanpa ubah app)
                               v
                         Storage: original/ | processed/ | temp/ (+retensi)
                               v
Android <-- download hasil -- Before/After slider -- Save/Share/Delete
```

API key & credential hanya di backend (`.env`, tak pernah di APK).
Android ↔ backend murni REST. Provider generatif (OpenAI, Phase 6) di belakang
interface `GenerativeEnhancer` — pipeline normal jalan tanpa API berbayar.

## 2. Struktur folder

```
photorestore/
  backend/app/   main.py jobs.py storage.py validate.py config.py
  worker/        tasks.py pipeline/{base,quality,basic,registry}.py
  android/       Kotlin (Retrofit, Coil, Material3)
  models/        download_weights.sh (Phase 3+; weights di-gitignore)
  tests/         make_samples.py test_api.py bench.py
  storage/       original/ processed/ temp/ cost-log.jsonl (dibuat saat jalan)
  docker-compose.yml  .env.example
```

## 3. Dependensi

Backend: Python 3.12, FastAPI, uvicorn, RQ, Redis, pydantic, python-multipart,
Pillow, numpy. Worker Phase 1: OpenCV. Phase 3+: torch, basicsr, facexlib,
gfpgan, realesrgan, retinaface/scrfd. Android: Kotlin, Retrofit/OkHttp, Coil.

## 4. Model open-source + lisensi (verifikasi 2026-10)

| Model | Fungsi | Lisensi | Komersial? |
|---|---|---|---|
| GFPGAN (+facexlib) | Face restoration utama | Apache-2.0 | YA |
| Real-ESRGAN | Upscale 2x/4x | BSD-3-Clause | YA |
| DDColor | Colorize B&W (opsional user) | Apache-2.0 | YA |
| RetinaFace / SCRFD | Deteksi wajah | MIT | YA |
| OpenCV | Denoise/klasik | Apache-2.0 | YA |
| CodeFormer | Alternatif wajah (opsional) | **S-Lab 1.0 non-komersial** | MINTA IZIN dulu |

Keputusan: **GFPGAN default** (natural + legal aman), CodeFormer hanya modul
opsional non-komersial. Fidelity default 0.7–0.9 (identitas dulu, detail kemudian).

## 5–6. Kebutuhan GPU / RAM / VRAM

| Tahap | Hardware | RAM/VRAM |
|---|---|---|
| Phase 1 (basic CPU) | Contabo sekarang cukup | ±100MB RSS/worker |
| HD (GFPGAN+ESRGAN 4x) | GPU 12GB+ (RTX 3060/4060) | 16GB RAM / 8–12GB VRAM |
| Ultra (difusi, Phase 6) | GPU 24GB (RTX 3090/4090) | 32GB RAM / 24GB VRAM |

## 7. Biaya per foto (Vast.ai RTX 3090 ±$0.10/jam)

Basic ±3 dtk ≈ $0.0001 (Rp2) · HD ±12 dtk ≈ $0.0004 (Rp6) ·
Ultra difusi ±60 dtk ≈ $0.0017 (Rp27). Contabo tetap ±$6/bln.
Cost-log (`storage/cost-log.jsonl`) mencatat waktu/mode/resolusi tiap job.

## Phase 1 — status: JALAN, teruji 2026-10-01

Upload → RQ job → OpenCV basic (quality score 0–100, denoise ringan bila
skor ≤80, CLAHE luminance, unsharp, Lanczos 2x) → PNG 2x → download.
Test: 8/8 validasi + alur lolos; benchmark 30/30 OK, rata-rata 2.2 dtk/foto,
RSS 32→100MB. Android: build lokal via Android Studio (isi API_BASE),
pola sama seperti APK selama ini.

## Phase 2 — status: JALAN, teruji 2026-10-01

Pipeline: Quality+ (blur/noise/brightness/contrast/artefak blok/grayscale/
jumlah wajah Haar + rekomendasi basic/hd/heavy) → Denoise adaptif
(dilewati bila noise rendah; bilateral cepat vs NlMeans) → Enhance →
Upscale modular (Lanczos selalu; Real-ESRGAN otomatis bila
USE_REALESRGAN=1 + torch + GPU; aturan <1000px=4x, >2000px=2x, configurable).
Test: unit quality 5/5 (tajam>buram, aturan skala), API 8/8, benchmark 30/30
OK rata-rata 2.7 dtk/foto.

## Phase 3 — status: JALAN, teruji 2026-10-01

Pipeline HD (7 tahap): quality → denoise → enhance → FaceDetect (YuNet bila
OpenCV mendukung, otomatis fallback Haar; box + confidence) → FaceRestore
modular (backend GFPGAN otomatis bila torch+GPU, kalau tidak klasik CPU
konservatif; fidelity 0.7–0.9; confidence rendah hanya polish ringan;
crop → restore → seamlessClone blend, bukan restore seluruh gambar) →
upscale → ColorEnhance (gray-world WB ±15%, gamma exposure, saturasi +10%
kecuali kulit via masker YCrCb).
API: mode `hd` + `fidelity` aktif; ultra tetap ditolak eksplisit.
Teruji: Lena (1 wajah, restored:1), API 8/8, benchmark 30/30 OK.

## Phase 4 — status: JALAN, teruji 2026-10-01

Deblur modular (`DeblurProcessor.process(image, strength)` light/medium/strong;
backend Richardson-Lucy FFT, backend AI tinggal tambah class). HD sekarang
ikut deblur. Mode **ultra**: deblur min medium + upscale paksa 4x + QC gate
(cek dimensi target, blur/noise diukur pada resolusi SAMA — pelajaran dari
false-reject lintas skala — tolak bila ketajaman anjlok/noise >40).
Android: pilihan mode basic/hd/ultra + slider fidelity.
Teruji: Lena ultra 9 tahap lolos QC (blur 449→1233, 512→2048, 2.5 dtk),
API 8/8, benchmark 30/30 OK.

## Phase 5 — status: JALAN (fallback aktif), teruji 2026-10-01

Backend API dan AI Worker dipisah sesuai spek 16: tahap berat (face_restore,
upscale, deblur) dipanggil via `POST {GPU_WORKER_URL}/v1/stage` oleh
`worker/pipeline/remote.py`; tahap ringan tetap lokal. Worker GPU
(`worker-gpu/server.py`: GFPGAN + Real-ESRGAN + RL, auth token, /health)
jalan di Vast.ai dari image ghcr (lihat `vast-gpu/` di branch vast/gpu-restore).
Spec 17: GPU mati/tidak ada → otomatis fallback CPU lokal (teruji),
job RQ retry 2x interval 2–10 mnt untuk gagal transient, timeout per job.
Cost-log mencatat `gpu:true/false` + nama backend tiap tahap.
PostgreSQL ditunda ke Phase 7 (baru butuh saat ada akun/limit); state job
di Redis terdokumentasi dan cukup untuk Phase 5.
Teruji: stub GPU 6/6 (remote 2x, fallback 3 tahap), API 8/8, bench 30/30 OK.
