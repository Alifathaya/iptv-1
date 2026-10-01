"""Foto Jelas v2 — backend proxy fal.ai (key tidak disimpan, hanya diteruskan)."""
import asyncio
import base64
import logging
import time

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fjv2")

app = FastAPI(title="Foto Jelas v2 proxy (fal.ai)")
QUEUE = "https://queue.fal.run"


class RestoreReq(BaseModel):
    mode: str = "enhance"  # enhance | colorize | full
    image: str  # dataURL jpeg/png
    fidelity: float = 0.7
    upscale: int = 2
    model_enhance: str = "fal-ai/codeformer"
    model_colorize: str = "fal-ai/ddcolor"
    extra: dict = {}


def _headers(key: str) -> dict:
    return {"Authorization": "Key " + key, "Content-Type": "application/json"}


async def _run(client: httpx.AsyncClient, key: str, model: str, inp: dict, label: str) -> str:
    s = await client.post(f"{QUEUE}/{model}", json={"input": inp}, headers=_headers(key))
    if s.status_code == 401:
        raise HTTPException(status_code=502, detail="fal 401 [key salah/kedaluwarsa]: ambil ulang di fal.ai/dashboard/keys")
    if s.status_code != 200:
        log.warning("submit %s -> %s %.500s", label, s.status_code, s.text)
        raise HTTPException(status_code=502, detail=f"fal {s.status_code} [{label}]: {s.text[:500]}")
    rid = s.json().get("request_id")
    if not rid:
        raise HTTPException(status_code=502, detail=f"fal [{label}]: tanpa request_id: {s.text[:300]}")
    t0 = time.time()
    while True:
        if time.time() - t0 > 420:
            raise HTTPException(status_code=504, detail=f"Timeout [{label}]")
        await asyncio.sleep(3)
        g = await client.get(f"{QUEUE}/{model}/requests/{rid}/status", headers=_headers(key))
        st = g.json().get("status", "")
        if st in ("COMPLETED",):
            break
        if st in ("FAILED", "CANCELLED"):
            log.warning("failed %s: %.500s", label, g.text)
            raise HTTPException(status_code=502, detail=f"Gagal [{label}]: {g.text[:500]}")
    r = await client.get(f"{QUEUE}/{model}/requests/{rid}", headers=_headers(key))
    data = r.json().get("data", {})
    img = data.get("image") or {}
    url = img.get("url") if isinstance(img, dict) else None
    if not url:
        raise HTTPException(status_code=502, detail=f"fal [{label}]: hasil kosong: {r.text[:300]}")
    log.info("%s OK", label)
    return url


@app.post("/api/restore")
async def restore(req: RestoreReq, x_fal_key: str = Header(default="")):
    key = (x_fal_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Key fal.ai kosong.")
    if req.mode not in ("enhance", "colorize", "full"):
        raise HTTPException(status_code=400, detail="mode harus enhance/colorize/full")
    async with httpx.AsyncClient(timeout=60) as client:
        if req.mode == "enhance":
            inp = {"image_url": req.image, "fidelity": req.fidelity,
                   "upscale_factor": req.upscale, "face_upscale": True}
            inp.update(req.extra)
            url = await _run(client, key, req.model_enhance, inp, "enhance")
        elif req.mode == "colorize":
            inp = {"image_url": req.image}
            inp.update(req.extra)
            url = await _run(client, key, req.model_colorize, inp, "colorize")
        else:
            inp1 = {"image_url": req.image}
            inp1.update((req.extra or {}).get("colorize", {}))
            colored = await _run(client, key, req.model_colorize, inp1, "full-1-colorize")
            inp2 = {"image_url": colored, "fidelity": req.fidelity,
                    "upscale_factor": req.upscale, "face_upscale": True}
            inp2.update((req.extra or {}).get("enhance", {}))
            url = await _run(client, key, req.model_enhance, inp2, "full-2-enhance")
        d = await client.get(url, timeout=120)
        if d.status_code != 200:
            return {"image_url": url}
        b64 = base64.b64encode(d.content).decode()
        mime = d.headers.get("content-type", "image/png").split(";")[0]
        return {"image_b64": f"data:{mime};base64,{b64}"}


@app.get("/api/health")
def health():
    return {"status": "ok", "provider": "fal.ai"}


app.mount("/", StaticFiles(directory="/tmp/fotojelas-v2/docs/fotojelas-v2", html=True), name="web")
