"""Storage: original/processed/temp terpisah + retensi + EXIF opsional."""
import io
import os
import time
import uuid

from PIL import Image

from . import config


def _ensure() -> dict:
    paths = {k: os.path.join(config.STORAGE_ROOT, k) for k in ("original", "processed", "temp")}
    for p in paths.values():
        os.makedirs(p, exist_ok=True)
    return paths


def save_original(raw: bytes, content_type: str) -> tuple:
    paths = _ensure()
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(content_type, ".jpg")
    job_id = uuid.uuid4().hex
    if not config.KEEP_EXIF:
        # tulis ulang tanpa metadata EXIF
        img = Image.open(io.BytesIO(raw))
        buf = io.BytesIO()
        fmt = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}.get(content_type, "JPEG")
        img.save(buf, format=fmt, quality=95)
        raw = buf.getvalue()
    path = os.path.join(paths["original"], job_id + ext)
    with open(path, "wb") as f:
        f.write(raw)
    return job_id, path


def processed_path(job_id: str) -> str:
    _ensure()
    return os.path.join(config.STORAGE_ROOT, "processed", job_id + ".png")


def cleanup() -> dict:
    """Hapus temp kedaluwarsa + original/processed lewat retensi. Jangan log isi file."""
    paths = _ensure()
    now = time.time()
    removed = {"temp": 0, "expired": 0}
    for name in os.listdir(paths["temp"]):
        p = os.path.join(paths["temp"], name)
        if now - os.path.getmtime(p) > config.TEMP_RETENTION_HOURS * 3600:
            os.remove(p)
            removed["temp"] += 1
    limit = config.RESULT_RETENTION_DAYS * 86400
    for sub in ("original", "processed"):
        for name in os.listdir(paths[sub]):
            p = os.path.join(paths[sub], name)
            if now - os.path.getmtime(p) > limit:
                os.remove(p)
                removed["expired"] += 1
    return removed
