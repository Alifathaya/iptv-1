"""Foto Jelas GPU server — GFPGAN (wajah) + Real-ESRGAN (background). Jalan di Vast.ai."""
import base64
import logging
import os

import cv2
import numpy as np
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fJGpu")

TOKEN = os.getenv("FJ_TOKEN", "")
app = FastAPI(title="Foto Jelas GPU")


class Req(BaseModel):
    mode: str = "enhance"
    image: str  # dataURL
    fidelity: float = 0.5  # 0..1, GFPGAN only_w=False; dipakai sebagai weight
    upscale: int = 2


_restorer = None


def _b64_to_img(data_url: str):
    try:
        b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
        raw = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=400, detail="image bukan base64 valid")
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="gagal decode gambar")
    return img


def get_restorer():
    global _restorer
    if _restorer is not None:
        return _restorer
    from basicsr.utils.download_util import load_file_from_url
    from gfpgan import GFPGANer
    from realesrgan import RealESRGANer
    from realesrgan.archs.srrnet_arch import RRDBNet
    import torch

    half = torch.cuda.is_available()
    log.info("cuda=%s", half)
    wdir = "/opt/restore/weights"
    os.makedirs(wdir, exist_ok=True)
    gfpgan_url = "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth"
    esrgan_url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
    gf_path = load_file_from_url(gfpgan_url, wdir)
    esr_path = load_file_from_url(esrgan_url, wdir)
    bg = RealESRGANer(
        scale=4, model_path=esr_path,
        model=RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4),
        tile=400, tile_pad=10, pre_pad=0, half=half,
    )
    _restorer = GFPGANer(
        model_path=gf_path, upscale=2, arch="clean", channel_multiplier=2,
        bg_upsampler=bg,
    )
    log.info("restorer siap")
    return _restorer


@app.get("/health")
def health():
    import torch

    return {"status": "ok", "cuda": torch.cuda.is_available()}


@app.post("/v1/restore")
def restore(req: Req, x_api_token: str = Header(default="")):
    if TOKEN and x_api_token != TOKEN:
        raise HTTPException(status_code=401, detail="token salah")
    if req.mode != "enhance":
        raise HTTPException(status_code=501, detail="mode colorize/full tahap 2 (masih via fal)")
    img = _b64_to_img(req.image)
    h, w = img.shape[:2]
    if max(h, w) > 2048:
        s = 2048 / max(h, w)
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    restorer = get_restorer()
    try:
        _, _, out = restorer.enhance(
            img, has_aligned=False, only_center_face=False, paste_back=True,
            weight=float(req.fidelity if 0 <= req.fidelity <= 1 else 0.5),
        )
    except Exception as e:
        log.exception("enhance gagal")
        raise HTTPException(status_code=500, detail=f"enhance gagal: {e}")
    if req.upscale == 4:
        out = cv2.resize(out, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    ok, buf = cv2.imencode(".png", out)
    if not ok:
        raise HTTPException(status_code=500, detail="encode gagal")
    b64 = base64.b64encode(bytes(buf)).decode()
    return {"image_b64": "data:image/png;base64," + b64, "width": out.shape[1], "height": out.shape[0]}
