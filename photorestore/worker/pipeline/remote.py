"""RemoteStage: jalankan tahap berat di GPU worker via HTTP.
Gagal/timeout -> GpuUnavailable agar pipeline fallback ke implementasi lokal
(spec 17: jangan crash, queued/retry di level job RQ)."""
import base64
import os

import cv2
import numpy as np
import httpx

GPU_URL = os.getenv("GPU_WORKER_URL", "").rstrip("/")
GPU_TOKEN = os.getenv("GPU_WORKER_TOKEN", "")
GPU_TIMEOUT = int(os.getenv("GPU_TIMEOUT", "300"))
GPU_RETRIES = int(os.getenv("GPU_RETRIES", "1"))


class GpuUnavailable(Exception):
    pass


def enabled() -> bool:
    return bool(GPU_URL)


def _to_b64(image: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("encode gagal")
    return "data:image/png;base64," + base64.b64encode(bytes(buf)).decode()


def _from_b64(data_url: str) -> np.ndarray:
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    img = cv2.imdecode(np.frombuffer(base64.b64decode(b64), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("decode hasil GPU gagal")
    return img


def run_stage(stage: str, image: np.ndarray, params: dict) -> np.ndarray:
    if not enabled():
        raise GpuUnavailable("GPU_WORKER_URL kosong")
    last = None
    for attempt in range(1 + GPU_RETRIES):
        try:
            r = httpx.post(GPU_URL + "/v1/stage",
                           json={"stage": stage, "image": _to_b64(image), "params": params},
                           headers={"X-Api-Token": GPU_TOKEN}, timeout=GPU_TIMEOUT)
            if r.status_code == 401:
                raise GpuUnavailable("token GPU salah")
            r.raise_for_status()
            return _from_b64(r.json()["image_b64"])
        except GpuUnavailable:
            raise
        except Exception as e:
            last = e
    raise GpuUnavailable(f"GPU {stage} gagal {1 + GPU_RETRIES}x: {last}")
