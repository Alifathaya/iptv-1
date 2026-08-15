# Foto Jelas Pro — GPU Backend

FastAPI server with **Real-ESRGAN** for cloud GPU photo enhancement.

## Quick start

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8080/health
```

Full deployment guide (Indonesian): **[DEPLOY-GPU.md](./DEPLOY-GPU.md)**

## Endpoints

- `GET /health` — GPU status
- `POST /v1/enhance` — upload image, get enhanced PNG

## CPU testing

```bash
docker compose -f docker-compose.cpu.yml up -d --build
```
