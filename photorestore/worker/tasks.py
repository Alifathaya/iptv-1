"""RQ task: jalankan pipeline, update progress, catat cost-log (tanpa data gambar)."""
import json
import os
import time

import cv2
from rq import get_current_job

from pipeline.registry import PIPELINES

COST_LOG = os.path.join(os.path.dirname(__file__), "..", "storage", "cost-log.jsonl")


def _progress(pct: int, status: str) -> None:
    try:
        job = get_current_job()
        if job is not None:
            job.meta["progress"] = pct
            job.meta["status"] = status
            job.save_meta()
    except Exception:
        pass


def run_enhance(job_id: str, src_path: str, mode: str, strength: str, fidelity: float = 0.8,
                generative: bool = False, prompt: str = "") -> dict:
    from backend.app import storage  # diimpor di sini agar path RQ fleksibel

    t0 = time.time()
    _progress(5, "processing")
    img = cv2.imread(src_path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("gagal baca gambar sumber")
    h0, w0 = img.shape[:2]
    ctx = {"strength": strength, "fidelity": fidelity, "in_wh": (w0, h0),
           "generative": bool(generative) and mode == "ultra", "prompt": prompt or ""}
    if mode == "ultra":
        # ultra: deblur minimal medium + upscale paksa 4x (maksimum resolusi)
        ctx["deblur_strength"] = {"light": "medium"}.get(strength, strength)
        ctx["force_scale"] = 4
    stages = PIPELINES[mode]
    _progress(20, "processing")
    used = []
    notes = {}
    for i, stage in enumerate(stages):
        res = stage.run(img, ctx)
        img = res.image
        used.append(stage.name)
        notes[stage.name] = res.notes
        _progress(20 + int(60 * (i + 1) / len(stages)), "processing")
    out_path = storage.processed_path(job_id)
    cv2.imwrite(out_path, img, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    dt = round(time.time() - t0, 2)
    h1, w1 = img.shape[:2]
    gpu = any("remote" in str(v.get("backend", "")) for v in notes.values() if isinstance(v, dict))
    entry = {"job_id": job_id, "mode": mode, "strength": strength,
             "stages": used, "stage_notes": notes, "seconds": dt,
             "in_wh": [w0, h0], "out_wh": [w1, h1],
             "quality": ctx.get("quality"), "gpu": gpu,
             "api_cost": round(ctx.get("api_cost", 0.0), 4)}
    os.makedirs(os.path.dirname(COST_LOG), exist_ok=True)
    with open(COST_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    _progress(100, "completed")
    return {"job_id": job_id, "seconds": dt}
