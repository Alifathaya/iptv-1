"""Job via RQ: enqueue + status (queued/processing/completed/failed) + progress 0-100."""
from redis import Redis
from rq import Queue
from rq.job import Job, Retry

from . import config

_redis = None
_queue = None


def get_queue() -> Queue:
    global _redis, _queue
    if _queue is None:
        _redis = Redis.from_url(config.REDIS_URL)
        _queue = Queue(config.QUEUE_NAME, connection=_redis)
    return _queue


def enqueue_enhance(job_id: str, src_path: str, mode: str, strength: str, fidelity: float = 0.8) -> str:
    q = get_queue()
    job = q.enqueue(
        "tasks.run_enhance",
        args=(job_id, src_path, mode, strength, fidelity),
        job_id=job_id,
        job_timeout=config.JOB_TIMEOUT,
        retry=Retry(max=2, interval=[120, 600]),  # retry otomatis utk gagal transient
        meta={"progress": 0, "status": "queued", "mode": mode},
    )
    return job.id


def job_status(job_id: str) -> dict:
    q = get_queue()
    try:
        job = Job.fetch(job_id, connection=q.connection)
    except Exception:
        return {"job_id": job_id, "status": "unknown"}
    meta = job.meta or {}
    out = {"job_id": job_id, "status": meta.get("status", "queued"),
           "progress": meta.get("progress", 0), "mode": meta.get("mode")}
    if job.is_failed:
        out["status"] = "failed"
        out["error"] = str(job.exc_info or "gagal")[:300].split("\n")[-1]
    elif meta.get("status") == "completed":
        out["result_url"] = f"{config.API_PREFIX}/result/{job_id}"
    return out
