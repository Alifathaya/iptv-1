"""Foto Jelas Pro — GPU backend API."""

from __future__ import annotations

import logging
from typing import Annotated, Literal

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .config import ALLOWED_ORIGINS, API_KEY, MAX_PIXELS, MAX_UPLOAD_BYTES
from .enhancer import enhancer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Foto Jelas Pro GPU API",
    description="Real-ESRGAN super-resolution backend for extreme photo enhancement",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health() -> dict:
    gpu = enhancer.gpu_info()
    return {
        "status": "ok",
        "service": "foto-jelas-gpu",
        "gpu": gpu,
    }


@app.get("/v1/info")
def info(_: None = Depends(verify_api_key)) -> dict:
    return {
        "models": ["RealESRGAN_x4plus", "RealESRGAN_x2plus"],
        "scales": [4, 8],
        "max_pixels": MAX_PIXELS,
        "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
    }


@app.post("/v1/enhance")
async def enhance_image(
    _: Annotated[None, Depends(verify_api_key)],
    image: UploadFile = File(...),
    scale: Annotated[int, Form()] = 4,
    deblur: Annotated[int, Form()] = 80,
    sharpness: Annotated[int, Form()] = 60,
    contrast: Annotated[int, Form()] = 25,
) -> Response:
    if scale not in (4, 8):
        raise HTTPException(status_code=400, detail="scale must be 4 or 8")

    contents = await image.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image too large")

    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    h, w = img.shape[:2]
    if h * w > MAX_PIXELS:
        ratio = (MAX_PIXELS / (h * w)) ** 0.5
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.info("Downscaled input %dx%d -> %dx%d", w, h, new_w, new_h)

    logger.info(
        "Enhance request: %dx%d scale=%d deblur=%d",
        img.shape[1], img.shape[0], scale, deblur,
    )

    try:
        result = enhancer.enhance(
            img,
            scale=scale,
            deblur_strength=deblur,
            sharpness=sharpness,
            contrast=contrast,
        )
    except Exception as exc:
        logger.exception("Enhancement failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    ok, png = cv2.imencode(".png", result)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode result")

    return Response(
        content=png.tobytes(),
        media_type="image/png",
        headers={
            "X-Output-Width": str(result.shape[1]),
            "X-Output-Height": str(result.shape[0]),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
