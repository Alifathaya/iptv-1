"""Job via RQ: enqueue + status (queued/processing/completed/failed) + progress 0-100."""
from redis import Redis
from rq import Queue
from rq.job import Job, Retry
from rq.registry import StartedJobRegistry

from . import config

_redis = None
_queue = None


def get_queue() -> Queue:
    global _redis, _queue
    if _queue is None:
        _redis = Redis.from_url(config.REDIS_URL)
        _queue = Queue(config.QUEUE_NAME, connection=_redis)
    return _queue


def enqueue_enhance(job_id: str, src_path: str, mode: str, strength: str, fidelity: float = 0.8,
                    generative: bool = False, prompt: str = "", user_id: int = 0) -> str:
    q = get_queue()
    job = q.enqueue(
        "tasks.run_enhance",
        args=(job_id, src_path, mode, strength, fidelity, generative, prompt, user_id),
        job_id=job_id,
        job_timeout=config.JOB_TIMEOUT,
        retry=Retry(max=2, interval=[120, 600]),  # retry otomatis utk gagal transient
        meta={"progress": 0, "status": "queued", "mode": mode, "user_id": user_id},
    )
    return job.id


def active_count(user_id: int) -> int:
    """Job antre + sedang jalan milik user (cadangan kuota anti-burst)."""
    q = get_queue()
    n = 0
    try:
        ids = list(q.job_ids) + StartedJobRegistry(queue=q).get_job_ids()
        for jid in ids:
            try:
                if Job.fetch(jid, connection=q.connection).meta.get("user_id") == user_id:
                    n += 1
            except Exception:
                pass
    except Exception:
        pass
    return n


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
