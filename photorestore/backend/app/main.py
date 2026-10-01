"""FotoRestore API — Phase 7: auth token + kuota Free/Premium."""
import logging
import os

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import config, db, jobs, storage
from .validate import validate_upload

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fotorestore")

app = FastAPI(title=config.APP_NAME)
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() == "true"


def current_user(x_api_key: str = Header(default="")) -> dict:
    if not REQUIRE_AUTH:
        return {"id": 0, "premium": True}  # dev lokal tanpa auth
    if not x_api_key:
        raise HTTPException(status_code=401, detail="butuh header X-Api-Key (daftar di POST /auth/register)")
    u = db.auth(x_api_key.strip())
    if not u:
        raise HTTPException(status_code=401, detail="API key salah")
    return u


@app.post("/auth/register")
def register():
    uid, token = db.create_user()
    return {"user_id": uid, "api_key": token,
            "warning": "simpan api_key ini, hanya tampil sekali"}


@app.get(config.API_PREFIX + "/me")
def me(user: dict = Depends(current_user)):
    return {"user_id": user["id"], "premium": user["premium"],
            "quota": db.quota(user["id"], user["premium"])}


@app.post("/admin/premium/{user_id}")
def make_premium(user_id: int, x_admin_token: str = Header(default="")):
    if not db.ADMIN_TOKEN or x_admin_token != db.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="admin saja")
    if not db.set_premium(user_id, True):
        raise HTTPException(status_code=404, detail="user tidak ada")
    return {"user_id": user_id, "premium": True}


@app.post(config.API_PREFIX + "/enhance")
async def enhance(file: UploadFile = File(...), mode: str = Form("basic"), strength: str = Form("medium"),
                  fidelity: float = Form(0.8), generative: bool = Form(False),
                  prompt: str = Form(""), user: dict = Depends(current_user)):
    if mode not in ("basic", "hd", "ultra"):
        raise HTTPException(status_code=400, detail=f"mode {mode} tidak dikenal (basic/hd/ultra)")
    if strength not in ("light", "medium", "strong"):
        raise HTTPException(status_code=400, detail="strength: light/medium/strong")
    if not 0.7 <= fidelity <= 0.9:
        raise HTTPException(status_code=400, detail="fidelity: 0.7-0.9")
    if not user["premium"]:
        used = db.daily_usage(user["id"]) + jobs.active_count(user["id"])
        if used >= db.FREE_DAILY_LIMIT:
            raise HTTPException(status_code=429,
                                detail=f"kuota gratis habis ({db.FREE_DAILY_LIMIT}/hari). Upgrade ke premium.")
    raw = validate_upload(file)
    job_id, src = storage.save_original(raw, file.content_type or "image/jpeg")
    jobs.enqueue_enhance(job_id, src, mode, strength, fidelity, generative, prompt[:500],
                         user["id"])
    log.info("job %s queued mode=%s user=%s", job_id, mode, user["id"])
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
    return {"status": "ok", "phase": 7}


@app.get("/test.html")
def test_page():
    return FileResponse(os.path.join(os.path.dirname(__file__), "test.html"),
                        media_type="text/html")
