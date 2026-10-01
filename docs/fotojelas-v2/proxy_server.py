"""Foto Jelas v2 — backend proxy Replicate (token tidak disimpan, hanya diteruskan)."""
import base64
import logging
import time

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fjv2")

app = FastAPI(title="Foto Jelas v2 proxy")
API = "https://api.replicate.com/v1"

MODELS = {
    "enhance": "sczhou/codeformer",
    "colorize": "piddnad/ddcolor",
}


class RestoreReq(BaseModel):
    mode: str = "enhance"  # enhance | colorize | full
    image: str  # dataURL jpeg/png
    fidelity: float = 0.7
    model_enhance: str = "sczhou/codeformer"
    model_colorize: str = "piddnad/ddcolor"
    extra: dict = {}


def _headers(token: str) -> dict:
    return {"Authorization": "Bearer " + token, "Content-Type": "application/json"}


async def _run(client: httpx.AsyncClient, token: str, model: str, inp: dict, label: str) -> str:
    r = await client.post(f"{API}/models/{model}/predictions", json={"input": inp}, headers=_headers(token))
    if r.status_code != 201:
        log.warning("create %s -> %s %.500s", label, r.status_code, r.text)
        raise HTTPException(status_code=502, detail=f"Replicate {r.status_code} [{label}]: {r.text[:500]}")
    p = r.json()
    t0 = time.time()
    while p.get("status") in ("starting", "processing"):
        if time.time() - t0 > 300:
            raise HTTPException(status_code=504, detail=f"Timeout [{label}]")
        await client.get(f"{API}/predictions/{p['id']}", headers=_headers(token))  # warm
        import asyncio

        await asyncio.sleep(2.5)
        g = await client.get(f"{API}/predictions/{p['id']}", headers=_headers(token))
        p = g.json()
    if p.get("status") != "succeeded":
        log.warning("failed %s: %.500s", label, str(p.get("error")))
        raise HTTPException(status_code=502, detail=f"Gagal [{label}]: {p.get('error') or p.get('status')}")
    out = p["output"]
    url = out[-1] if isinstance(out, list) else out
    log.info("%s OK -> %.120s", label, url)
    return url


@app.post("/api/restore")
async def restore(req: RestoreReq, x_replicate_token: str = Header(default="")):
    token = (x_replicate_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token Replicate kosong.")
    if req.mode not in ("enhance", "colorize", "full"):
        raise HTTPException(status_code=400, detail="mode harus enhance/colorize/full")
    async with httpx.AsyncClient(timeout=60) as client:
        cur = req.image
        if req.mode == "enhance":
            inp = {"image": cur, "face_upsample": True, "background_enhance": True,
                   "codeformer_fidelity": req.fidelity, "upscale": 2}
            inp.update(req.extra)
            cur = await _run(client, token, req.model_enhance, inp, "enhance")
        elif req.mode == "colorize":
            inp = {"image": cur}
            inp.update(req.extra)
            cur = await _run(client, token, req.model_colorize, inp, "colorize")
        else:
            inp1 = {"image": cur}
            inp1.update((req.extra or {}).get("colorize", {}))
            cur = await _run(client, token, req.model_colorize, inp1, "full-1-colorize")
            inp2 = {"image": cur, "face_upsample": True, "background_enhance": True,
                    "codeformer_fidelity": req.fidelity, "upscale": 2}
            inp2.update((req.extra or {}).get("enhance", {}))
            cur = await _run(client, token, req.model_enhance, inp2, "full-2-enhance")
        # unduh hasil lewat server agar browser tidak kena CORS output
        d = await client.get(cur, timeout=120)
        if d.status_code != 200:
            return {"image_url": cur}
        b64 = base64.b64encode(d.content).decode()
        mime = d.headers.get("content-type", "image/png").split(";")[0]
        return {"image_b64": f"data:{mime};base64,{b64}"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="/tmp/fotojelas-v2/docs/fotojelas-v2", html=True), name="web")
