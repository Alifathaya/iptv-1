"""FotoRestore API — Phase 1: upload, job async, hasil."""
import logging
import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import config, jobs, storage
from .validate import validate_upload

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fotorestore")

app = FastAPI(title=config.APP_NAME)


@app.post(config.API_PREFIX + "/enhance")
async def enhance(file: UploadFile = File(...), mode: str = Form("basic"), strength: str = Form("medium")):
    if mode != "basic":
        # HD/Ultra aktif mulai Phase 3 (butuh model wajah). Bukan placeholder:
        # request ditolak eksplisit agar klien tidak menunggu hasil yang tak ada.
        raise HTTPException(status_code=400, detail=f"mode {mode} belum tersedia di Phase 1 (baru: basic)")
    if strength not in ("light", "medium", "strong"):
        raise HTTPException(status_code=400, detail="strength: light/medium/strong")
    raw = validate_upload(file)
    job_id, src = storage.save_original(raw, file.content_type or "image/jpeg")
    jobs.enqueue_enhance(job_id, src, mode, strength)
    log.info("job %s queued mode=%s strength=%s", job_id, mode, strength)
    return {"job_id": job_id, "status": "queued"}


@app.get(config.API_PREFIX + "/jobs/{job_id}")
def get_job(job_id: str):
    return jobs.job_status(job_id)


@app.get(config.API_PREFIX + "/result/{job_id}")
def get_result(job_id: str):
    path = storage.processed_path(job_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="hasil belum ada / job_id salah")
    return FileResponse(path, media_type="image/png")


@app.delete(config.API_PREFIX + "/result/{job_id}")
def delete_result(job_id: str):
    removed = []
    for sub in ("original", "processed"):
        for ext in (".jpg", ".png", ".webp"):
            p = os.path.join(config.STORAGE_ROOT, sub, job_id + ext)
            if os.path.exists(p):
                os.remove(p)
                removed.append(sub)
    return {"job_id": job_id, "deleted": removed}


@app.get("/health")
def health():
    return {"status": "ok", "phase": 1}
