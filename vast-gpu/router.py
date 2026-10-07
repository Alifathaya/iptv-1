"""Router hybrid (system python, stdlib saja): FLUX -> GFPGAN.
POST /v1/restore {image, fidelity, strength, steps, upscale}
 1. FLUX 127.0.0.1:8001 (perbaiki kerusakan + warnai)
 2. GFPGAN 127.0.0.1:8002 (wajah, jangkar identitas)
"""
import base64
import json
import logging
import urllib.request

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("hybrid")

import os

TOKEN = os.getenv("FJ_TOKEN", "")
app = FastAPI(title="FotoRestore hybrid")


class Req(BaseModel):
    image: str
    fidelity: float = 0.8
    strength: float = 0.42
    steps: int = 4
    upscale: int = 2


def _post(url: str, payload: dict, timeout: int):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Api-Token": TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        raise RuntimeError(f"{url}: {e}")


def _ok(port: int) -> bool:
    import socket

    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=5)
        s.close()
        return True
    except OSError:
        return False


@app.get("/health")
def health():
    return {"status": "ok", "flux": _ok(8001), "gfpgan": _ok(8002)}


@app.post("/v1/restore")
def restore(req: Req, x_api_token: str = Header(default="")):
    if TOKEN and x_api_token != TOKEN:
        raise HTTPException(status_code=401, detail="token salah")
    try:
        f = _post("http://127.0.0.1:8001/v1/stage",
                  {"stage": "flux_restore", "image": req.image,
                   "params": {"strength": req.strength, "steps": req.steps,
                              "max_side": 768, "repair": True, "sharpen": False}},
                  timeout=600)
        flux_b64 = f["image_b64"]
    except Exception as e:
        log.exception("flux gagal")
        raise HTTPException(status_code=500, detail=f"flux gagal: {e}")
    try:
        g = _post("http://127.0.0.1:8002/v1/restore",
                  {"image": flux_b64, "fidelity": max(0.7, min(0.9, req.fidelity)),
                   "upscale": req.upscale},
                  timeout=600)
    except Exception as e:
        log.exception("gfpgan gagal")
        raise HTTPException(status_code=500, detail=f"gfpgan gagal: {e}")
    return {"image_b64": g["image_b64"],
            "meta": {"pipeline": "flux-0.42 -> gfpgan",
                     "flux": f.get("meta", {}), "strength": req.strength}}
