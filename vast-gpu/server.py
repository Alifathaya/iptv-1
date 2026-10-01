"""AI Worker GPU — stage terpisah dari Backend API (spec 16).
Endpoint /v1/stage mengeksekusi SATU tahap berat per request sehingga
backend bisa campur: tahap ringan lokal CPU, tahap berat di sini.
Jalan di Vast.ai (lihat vast-gpu/Dockerfile); backend di Contabo.
Tanpa GPU: backend otomatis fallback ke implementasi CPU lokal."""
import base64
import logging
import os

import cv2
import numpy as np
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gpuworker")

TOKEN = os.getenv("FJ_TOKEN", "")
WDIR = os.getenv("MODEL_DIR", "/opt/restore/weights")

app = FastAPI(title="FotoRestore GPU worker")


class StageReq(BaseModel):
    stage: str  # face_restore | upscale | deblur
    image: str  # dataURL
    params: dict = {}


def _img(data_url: str):
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    img = cv2.imdecode(np.frombuffer(base64.b64decode(b64), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="gambar tidak valid")
    return img


def _out(img) -> str:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise HTTPException(status_code=500, detail="encode gagal")
    return "data:image/png;base64," + base64.b64encode(bytes(buf)).decode()


_gfpgan_model = None
_esrgan_model = None


def _gfpgan():
    global _gfpgan_model
    if _gfpgan_model is None:
        import torch
        from gfpgan import GFPGANer

        if not torch.cuda.is_available():
            raise RuntimeError("butuh CUDA")
        _gfpgan_model = GFPGANer(model_path=os.path.join(WDIR, "GFPGANv1.4.pth"), upscale=1,
                           arch="clean", channel_multiplier=2, bg_upsampler=None)
    return _gfpgan_model


def _esrgan():
    global _esrgan_model
    if _esrgan_model is None:
        import torch
        from basicsr.utils.download_util import load_file_from_url
        from realesrgan import RealESRGANer
        from basicsr.archs.rrdbnet_arch import RRDBNet

        half = torch.cuda.is_available()
        if not half:
            raise RuntimeError("butuh CUDA")
        os.makedirs(WDIR, exist_ok=True)
        path = os.path.join(WDIR, "RealESRGAN_x4plus.pth")
        if not os.path.exists(path):
            path = load_file_from_url(
                "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth", WDIR)
        _esrgan_model = RealESRGANer(
            scale=4, model_path=path,
            model=RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                          num_block=23, num_grow_ch=32, scale=4),
            tile=400, tile_pad=10, pre_pad=0, half=half)
    return _esrgan_model


@app.get("/health")
def health():
    try:
        import torch

        cuda = torch.cuda.is_available()
    except ImportError:
        cuda = False
    return {"status": "ok", "cuda": cuda}


@app.post("/v1/stage")
def stage(req: StageReq, x_api_token: str = Header(default="")):
    if TOKEN and x_api_token != TOKEN:
        raise HTTPException(status_code=401, detail="token salah")
    img = _img(req.image)
    try:
        if req.stage == "face_restore":
            fid = float(req.params.get("fidelity", 0.8))
            faces = req.params.get("faces", [])
            out = _do_faces(img, faces, fid)
        elif req.stage == "upscale":
            scale = int(req.params.get("scale", 4))
            out, _ = _esrgan().enhance(img, outscale=scale)
        elif req.stage == "deblur":
            out = _do_deblur(img, req.params.get("strength", "strong"))
        else:
            raise HTTPException(status_code=400, detail=f"stage {req.stage} tak dikenal")
    except HTTPException:
        raise
    except Exception as e:
        log.exception("stage %s gagal", req.stage)
        raise HTTPException(status_code=500, detail=f"{req.stage} gagal: {e}")
    return {"image_b64": _out(out)}


def _do_faces(img, faces, fidelity):
    import cv2 as cv

    r = _gfpgan()
    out = img
    for f in faces:
        x, y, bw, bh = f["box"]
        ex, ey = int(bw * 0.25), int(bh * 0.25)
        x, y = max(0, x - ex), max(0, y - ey)
        bw, bh = min(img.shape[1] - x, bw + 2 * ex), min(img.shape[0] - y, bh + 2 * ey)
        crop = out[y:y + bh, x:x + bw].copy()
        if crop.size == 0:
            continue
        if f.get("score", 0) < 0.75:
            blur = cv.GaussianBlur(crop, (0, 0), 1.0)
            patch = cv.addWeighted(crop, 1.1, blur, -0.1, 0)
        else:
            _, _, patch = r.enhance(crop, has_aligned=False, only_center_face=True,
                                    paste_back=True, weight=max(0.7, min(0.9, fidelity)))
        mask = np.full((bh, bw), 255, np.uint8)
        try:
            out = cv.seamlessClone(patch, out, mask, (x + bw // 2, y + bh // 2), cv.NORMAL_CLONE)
        except cv.error:
            out[y:y + bh, x:x + bw] = patch
    return out


def _do_deblur(img, strength):
    import numpy as _np
    from numpy.fft import fft2, ifft2

    params = {"light": (5, 1.0, 5), "medium": (9, 2.0, 10), "strong": (15, 3.0, 15)}
    k, sigma, iters = params.get(strength, params["strong"])
    ax = _np.arange(k) - k // 2
    xx, yy = _np.meshgrid(ax, ax)
    psf = _np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma ** 2))
    psf /= psf.sum()
    out_ch = []
    for c in cv2.split(img):
        h, w = c.shape
        H = fft2(psf, s=(h, w))
        Hc = _np.conj(H)
        est = c.astype(_np.float64) + 1.0
        tgt = est.copy()
        for _ in range(iters):
            conv = _np.real(ifft2(fft2(est) * H))
            rel = tgt / _np.maximum(conv, 1e-6)
            est = _np.clip(est * _np.real(ifft2(fft2(rel) * Hc)), 0, 255)
        out_ch.append((est - 1.0).clip(0, 255).astype(_np.uint8))
    return cv2.merge(out_ch)
