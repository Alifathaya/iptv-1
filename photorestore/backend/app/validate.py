"""Validasi upload: tipe, ukuran, dimensi, file rusak."""
import io

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile

from . import config

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def validate_upload(up: UploadFile) -> bytes:
    if up.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail=f"tipe {up.content_type} tidak didukung (jpg/png/webp)")
    raw = up.file.read()
    if len(raw) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"maks {config.MAX_UPLOAD_MB}MB")
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="file kosong")
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="file rusak / bukan gambar valid")
    h, w = img.shape[:2]
    if min(h, w) < config.MIN_DIMENSION:
        raise HTTPException(status_code=400, detail=f"terlalu kecil (min {config.MIN_DIMENSION}px)")
    if max(h, w) > config.MAX_DIMENSION:
        raise HTTPException(status_code=400, detail=f"terlalu besar (maks {config.MAX_DIMENSION}px)")
    return raw
