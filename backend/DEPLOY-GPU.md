# Deploy Backend GPU — Foto Jelas Pro

Backend **Real-ESRGAN** di server NVIDIA GPU untuk hasil terbaik pada foto blur ekstrem.

## Arsitektur

```
[App Android/Web]  ──upload foto──▶  [FastAPI GPU Server]
                                         │
                                    Real-ESRGAN 4x
                                    Real-ESRGAN 2x (untuk 8x)
                                         │
                                    PNG hasil HD ──▶  App
```

## Persyaratan server

| Komponen | Minimum |
|----------|---------|
| GPU | NVIDIA dengan CUDA (GTX 1060 6GB+) |
| VRAM | 6GB+ (8GB+ untuk foto besar) |
| RAM | 8GB+ |
| OS | Ubuntu 22.04 / Debian |
| Software | Docker + NVIDIA Container Toolkit |

---

## Deploy cepat (Docker GPU)

### 1. Install NVIDIA Container Toolkit

```bash
# Ubuntu
curl -fsSL https://get.docker.com | sh
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 2. Clone & konfigurasi

```bash
cd iptv-1/backend
cp .env.example .env
# Edit .env — set API_KEY dan ALLOWED_ORIGINS
```

**Penting:** Tambahkan URL GitHub Pages Anda di `ALLOWED_ORIGINS`:

```env
API_KEY=rahasia-kunci-api-anda
ALLOWED_ORIGINS=https://alifathaya.github.io,capacitor://localhost,https://localhost
```

### 3. Jalankan

```bash
docker compose up -d --build
```

Pertama kali build memakan waktu (~10–20 menit). Model weights diunduh otomatis saat pertama request.

### 4. Tes

```bash
curl http://localhost:8080/health
```

Respon contoh:

```json
{
  "status": "ok",
  "gpu": { "available": true, "name": "NVIDIA GeForce RTX 3060" }
}
```

---

## Tanpa GPU (CPU only — testing)

```bash
docker compose -f docker-compose.cpu.yml up -d --build
```

Lebih lambat, tapi bisa untuk uji coba.

---

## Hubungkan ke App

1. Buka Foto Jelas Pro (web atau APK)
2. Pilih mode **☁️ GPU 4x** atau **🚀 GPU 8x MAX**
3. Isi **URL API**: `http://IP-SERVER:8080` atau `https://gpu.domain.com`
4. Isi **API Key** (jika di-set di `.env`)
5. Klik **Tes Koneksi** → harus ✓ Terhubung
6. Upload foto buram

---

## API Endpoints

| Endpoint | Auth | Deskripsi |
|----------|------|-----------|
| `GET /health` | Tidak | Status + info GPU |
| `GET /v1/info` | API Key* | Info model & limit |
| `POST /v1/enhance` | API Key* | Enhance foto |

\* API Key hanya wajib jika `API_KEY` di-set di environment.

### POST /v1/enhance

| Field | Tipe | Default | Deskripsi |
|-------|------|---------|-----------|
| `image` | file | — | JPG/PNG/WebP |
| `scale` | int | 4 | `4` atau `8` |
| `deblur` | int | 80 | Kekuatan deblur 0–100 |
| `sharpness` | int | 60 | Ketajaman akhir |
| `contrast` | int | 25 | Kontras akhir |

Header: `X-API-Key: your-key` (jika auth aktif)

Respon: PNG image

---

## Deploy di cloud GPU

### RunPod / Vast.ai / Lambda

1. Pilih template: **Ubuntu 22.04 + CUDA**
2. GPU: RTX 3090 / A10 / T4 (murah)
3. SSH ke instance, install Docker + NVIDIA toolkit
4. Clone repo, `docker compose up -d --build`
5. Buka port **8080** di firewall
6. (Opsional) Pasang Nginx + SSL dengan Let's Encrypt

### Contoh Nginx reverse proxy

```nginx
server {
    listen 443 ssl;
    server_name gpu.example.com;

    ssl_certificate /etc/letsencrypt/live/gpu.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gpu.example.com/privkey.pem;

    client_max_body_size 30M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

---

## Estimasi biaya cloud

| Provider | GPU | ~Harga/jam | Cocok untuk |
|----------|-----|------------|-------------|
| Vast.ai | RTX 3060 | $0.10–0.20 | Personal |
| RunPod | RTX 4090 | $0.40–0.70 | Produksi |
| Lambda | A10 | $0.60–1.00 | High traffic |

Matikan instance saat tidak dipakai untuk hemat biaya.

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `gpu.available: false` | Cek `nvidia-smi`, NVIDIA toolkit, restart Docker |
| CORS error di browser | Tambahkan origin di `ALLOWED_ORIGINS` |
| 401 Unauthorized | Samakan API Key app dan server |
| Out of memory | Kurangi `TILE_SIZE=256` di `.env` |
| Lambat | Normal untuk 8x — gunakan GPU lebih kuat |
| Build gagal | Cek disk space (butuh ~5GB untuk image) |

---

## Keamanan

- **Selalu** set `API_KEY` untuk server publik
- Gunakan HTTPS (Nginx + SSL)
- Batasi `ALLOWED_ORIGINS` — jangan pakai `*` di produksi
- Monitor penggunaan GPU & bandwidth
