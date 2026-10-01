# GPU Vast.ai — Foto Jelas restore server

Tahap 1: **enhance** (GFPGAN wajah + Real-ESRGAN background) di GPU sewaan.
Warnai/full tetap via fal.ai (murah) sampai DDColor dipasang tahap 2.

## File
- `server.py` — FastAPI di instance GPU, port 8000, auth `X-Api-Token: $FJ_TOKEN`
- `setup.sh` — dipanggil via onstart Vast.ai

## Deploy (dilakukan agent, butuh ~/.vast-api-key di VPS + kredit Vast.ai)
1. Cari offer RTX 3090 on-demand:
   `GET /api/v0/bundles/?q={"gpu_name":"RTX_3090","num_gpus":1,"order":["dph_total","asc"]}`
2. Buat instance:
   `PUT /api/v0/asks/{id}/` body
   `{"image":"pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime","disk":40,`
   ` "env":"-e FJ_TOKEN=xxx -e FJ_BRANCH=vast/gpu-restore",`
   ` "onstart":"curl -sL https://raw.githubusercontent.com/Alifathaya/iptv-1/vast/gpu-restore/vast-gpu/setup.sh -o /tmp/setup.sh && bash /tmp/setup.sh"}`
3. Tunggu `actual_status=running`, ambil IP + port mapping 8000/tcp dari detail instance.
4. Test: `POST http://IP:PORT/v1/restore` + `GET /health` (cek cuda=true).
5. Arahkan proxy Contabo (`/opt/fotojelas-proxy`) ke Vast untuk mode enhance.

## Biaya (RTX 3090 ~$0.10/jam)
- Full enhance ~10 dtk/foto ≈ $0.0003/foto. 1000 foto ≈ $0.30.
- Instance nganggur: stop/destroy. Storage tetap jalan selama instance ada.
