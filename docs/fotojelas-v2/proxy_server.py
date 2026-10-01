"""Foto Jelas v2 — proxy: enhance via GPU Vast.ai (kalau ada), warnai via fal.ai."""
import asyncio
import base64
import json
import logging
import os
import time

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fjv2")

app = FastAPI(title="Foto Jelas v2 proxy")
QUEUE = "https://queue.fal.run"
VAST_API = "https://console.vast.ai/api/v0"
VAST_API_V1 = "https://console.vast.ai/api/v1"
VAST_KEY_FILE = os.path.expanduser("~/.vast-api-key")
VAST_STATE_FILE = "/opt/fotojelas-proxy/vast.json"
IDLE_MINUTES = 15  # destroy GPU kalau nganggur selama ini (nol total)
DEPLOYING: dict = {"active": False, "msg": ""}


class RestoreReq(BaseModel):
    mode: str = "enhance"  # enhance | colorize | full
    image: str  # dataURL jpeg/png
    fidelity: float = 0.7
    upscale: int = 2
    model_enhance: str = "fal-ai/codeformer"
    model_colorize: str = "fal-ai/ddcolor"
    extra: dict = {}


def _headers(key: str) -> dict:
    return {"Authorization": "Key " + key, "Content-Type": "application/json"}


async def _run(client: httpx.AsyncClient, key: str, model: str, inp: dict, label: str) -> str:
    model = (model or "").strip()
    if "/" not in model:
        model = "fal-ai/" + model
    s = await client.post(f"{QUEUE}/{model}", json={"input": inp}, headers=_headers(key))
    if s.status_code == 401:
        raise HTTPException(status_code=502, detail="fal 401 [key salah/kedaluwarsa]: ambil ulang di fal.ai/dashboard/keys")
    if s.status_code != 200:
        log.warning("submit %s -> %s %.500s", label, s.status_code, s.text)
        raise HTTPException(status_code=502, detail=f"fal {s.status_code} [{label}]: {s.text[:500]}")
    rid = s.json().get("request_id")
    if not rid:
        raise HTTPException(status_code=502, detail=f"fal [{label}]: tanpa request_id: {s.text[:300]}")
    t0 = time.time()
    while True:
        if time.time() - t0 > 420:
            raise HTTPException(status_code=504, detail=f"Timeout [{label}]")
        await asyncio.sleep(3)
        g = await client.get(f"{QUEUE}/{model}/requests/{rid}/status", headers=_headers(key))
        st = g.json().get("status", "")
        if st in ("COMPLETED",):
            break
        if st in ("FAILED", "CANCELLED"):
            log.warning("failed %s: %.500s", label, g.text)
            raise HTTPException(status_code=502, detail=f"Gagal [{label}]: {g.text[:500]}")
    r = await client.get(f"{QUEUE}/{model}/requests/{rid}", headers=_headers(key))
    data = r.json().get("data", {})
    img = data.get("image") or {}
    url = img.get("url") if isinstance(img, dict) else None
    if not url:
        raise HTTPException(status_code=502, detail=f"fal [{label}]: hasil kosong: {r.text[:300]}")
    log.info("%s OK", label)
    return url


@app.post("/api/restore")
async def restore(req: RestoreReq, x_fal_key: str = Header(default="")):
    if req.mode not in ("enhance", "colorize", "full"):
        raise HTTPException(status_code=400, detail="mode harus enhance/colorize/full")
    provider = "fal"
    async with httpx.AsyncClient(timeout=60) as client:
        if req.mode == "enhance":
            key = (x_fal_key or "").strip()
            if _vast_configured():
                try:
                    b64 = await _vast_enhance(client, req.image, req.fidelity, req.upscale)
                    return {"image_b64": b64, "provider": "vast-gpu"}
                except HTTPException:
                    raise
                except Exception as e:
                    log.warning("vast gagal, fallback fal: %s", e)
            if not key:
                raise HTTPException(status_code=400, detail="Key fal.ai kosong (dan GPU Vast belum aktif).")
            inp = {"image_url": req.image, "fidelity": req.fidelity,
                   "upscale_factor": req.upscale, "face_upscale": True}
            inp.update(req.extra)
            url = await _run(client, key, req.model_enhance, inp, "enhance")
        elif req.mode == "colorize":
            key = (x_fal_key or "").strip()
            if not key:
                raise HTTPException(status_code=400, detail="Key fal.ai kosong.")
            inp = {"image_url": req.image}
            inp.update(req.extra)
            url = await _run(client, key, req.model_colorize, inp, "colorize")
        else:
            key = (x_fal_key or "").strip()
            if not key:
                raise HTTPException(status_code=400, detail="Key fal.ai kosong.")
            inp1 = {"image_url": req.image}
            inp1.update((req.extra or {}).get("colorize", {}))
            colored = await _run(client, key, req.model_colorize, inp1, "full-1-colorize")
            if _vast_configured():
                try:
                    b64 = await _vast_enhance(client, colored, req.fidelity, req.upscale)
                    return {"image_b64": b64, "provider": "vast-gpu"}
                except HTTPException:
                    raise
                except Exception as e:
                    log.warning("vast gagal, fallback fal: %s", e)
            inp2 = {"image_url": colored, "fidelity": req.fidelity,
                    "upscale_factor": req.upscale, "face_upscale": True}
            inp2.update((req.extra or {}).get("enhance", {}))
            url = await _run(client, key, req.model_enhance, inp2, "full-2-enhance")
        d = await client.get(url, timeout=120)
        if d.status_code != 200:
            return {"image_url": url, "provider": provider}
        b64 = base64.b64encode(d.content).decode()
        mime = d.headers.get("content-type", "image/png").split(";")[0]
        return {"image_b64": f"data:{mime};base64,{b64}", "provider": provider}


# ---------- Vast.ai GPU (auto start/stop) ----------

def _vast_key() -> str:
    try:
        with open(VAST_KEY_FILE) as f:
            return f.read().strip()
    except OSError:
        return ""


def _vast_configured() -> bool:
    if not _vast_key():
        return False
    try:
        with open(VAST_STATE_FILE) as f:
            return bool(json.load(f).get("instance_id"))
    except OSError:
        return False


def _vast_headers() -> dict:
    return {"Authorization": "Bearer " + _vast_key(), "Content-Type": "application/json"}


def _vast_state() -> dict:
    try:
        with open(VAST_STATE_FILE) as f:
            return json.load(f)
    except OSError:
        return {}


def _vast_save(state: dict) -> None:
    with open(VAST_STATE_FILE, "w") as f:
        json.dump(state, f)


async def _vast_instance(client: httpx.AsyncClient, iid: int) -> dict:
    r = await client.get(f"{VAST_API_V1}/instances/{iid}/", headers=_vast_headers())
    r.raise_for_status()
    insts = r.json().get("instances", {})
    return insts.get(str(iid), {}) if isinstance(insts, dict) else {}


def _vast_endpoint(inst: dict) -> str:
    ip = inst.get("public_ipaddr") or ""
    ports = inst.get("ports") or {}
    for name, maps in ports.items():
        if str(name).startswith("8000/") and maps:
            return f"http://{ip}:{maps[0].get('HostPort')}"
    return ""


async def _vast_ensure_running(client: httpx.AsyncClient) -> dict:
    st = _vast_state()
    iid = st.get("instance_id")
    if not iid:
        raise RuntimeError("GPU belum dinyalakan. Tekan tombol Nyalakan GPU di panel Pengaturan, tunggu ±20 menit, lalu coba lagi.")
    inst = await _vast_instance(client, iid)
    status = inst.get("actual_status")
    if status != "running":
        log.info("vast %s status=%s -> start", iid, status)
        r = await client.put(f"{VAST_API_V1}/instances/{iid}/", json={"state": "running"}, headers=_vast_headers())
        if not r.json().get("success", True):
            raise RuntimeError(f"start gagal: {r.text[:200]}")
        t0 = time.time()
        while time.time() - t0 < 600:
            await asyncio.sleep(15)
            inst = await _vast_instance(client, iid)
            status = inst.get("actual_status")
            if status == "running":
                break
            if status in ("exited", "unknown", "offline"):
                raise RuntimeError(f"instance {status}, hubungi admin")
        else:
            raise RuntimeError("instance tidak running dalam 10 menit")
    ep = _vast_endpoint(inst)
    if not ep:
        raise RuntimeError("port 8000 instance tidak ketemu")
    # tunggu program GPU selesai setup (download model ±20 mnt pertama kali)
    t0 = time.time()
    while time.time() - t0 < 1800:
        try:
            h = await client.get(ep + "/health", timeout=10)
            if h.status_code == 200:
                break
        except Exception:
            pass
        await asyncio.sleep(20)
    else:
        raise RuntimeError("program GPU tidak siap dalam 30 menit, cek setup.log instance")
    st["last_used"] = time.time()
    _vast_save(st)
    return {"endpoint": ep, "token": st.get("gpu_token", "")}


async def _vast_destroy(client: httpx.AsyncClient, iid: int) -> None:
    try:
        await client.delete(f"{VAST_API_V1}/instances/{iid}/", headers=_vast_headers())
        log.info("vast %s destroyed (langsung sehabis 1 foto)", iid)
    except Exception as e:
        log.warning("destroy %s gagal: %s", iid, e)
    st = _vast_state()
    st.pop("instance_id", None)
    st["last_used"] = 0
    _vast_save(st)


async def _vast_enhance(client: httpx.AsyncClient, image: str, fidelity: float, upscale: int) -> str:
    info = await _vast_ensure_running(client)
    r = await client.post(
        info["endpoint"] + "/v1/restore",
        json={"mode": "enhance", "image": image, "fidelity": fidelity, "upscale": upscale},
        headers={"X-Api-Token": info["token"]},
        timeout=600,
    )
    if r.status_code != 200:
        raise RuntimeError(f"gpu {r.status_code}: {r.text[:300]}")
    b64 = r.json().get("image_b64")
    if not b64:
        raise RuntimeError("gpu hasil kosong")
    # hasil sudah di tangan -> destroy langsung (nol total), watchdog jadi cadangan
    st = _vast_state()
    if st.get("instance_id"):
        await _vast_destroy(client, st["instance_id"])
    return b64


async def _vast_watchdog() -> None:
    while True:
        await asyncio.sleep(60)
        try:
            st = _vast_state()
            iid = st.get("instance_id")
            last = st.get("last_used", 0)
            if not iid or not last or time.time() - last < IDLE_MINUTES * 60:
                continue
            async with httpx.AsyncClient(timeout=30) as client:
                inst = await _vast_instance(client, iid)
                if inst.get("actual_status") in ("running", "loading", None):
                    await client.delete(f"{VAST_API_V1}/instances/{iid}/", headers=_vast_headers())
                    log.info("vast %s auto-destroy (nganggur %s mnt) -> nol total", iid, IDLE_MINUTES)
            st = _vast_state()
            st.pop("instance_id", None)
            st["last_used"] = 0
            _vast_save(st)
        except Exception as e:
            log.warning("watchdog: %s", e)


def _pick_offer(offers: list) -> dict:
    cands = []
    for o in offers:
        if not o.get("rentable"):
            continue
        name = str(o.get("gpu_name", ""))
        if "3090" not in name and "4090" not in name and "A5000" not in name:
            continue
        if (o.get("reliability2") or 0) < 0.95:
            continue
        if (o.get("cuda_max_good") or 0) < 12.0:
            continue
        cands.append(o)
    if not cands:
        return {}
    cands.sort(key=lambda o: o.get("dph_total", 9e9))
    return cands[0]


async def _vast_deploy_job() -> None:
    if DEPLOYING["active"]:
        return
    DEPLOYING.update(active=True, msg="mencari GPU termurah...")
    try:
        import secrets

        async with httpx.AsyncClient(timeout=60) as client:
            q = {"gpu_name": "RTX 3090", "rentable": True, "order": [["dph_total", "asc"]]}
            import urllib.parse

            r = await client.get(
                f"{VAST_API}/bundles/?q={urllib.parse.quote_plus(__import__('json').dumps(q))}",
                headers=_vast_headers(),
            )
            offers = (r.json().get("offers") or []) if r.status_code == 200 else []
            offer = _pick_offer(offers)
            if not offer:
                DEPLOYING["msg"] = "tidak ada offer 3090/4090/A5000 yang cocok saat ini"
                return
            token = secrets.token_hex(16)
            onstart = (
                "curl -sL https://raw.githubusercontent.com/Alifathaya/iptv-1/"
                "vast/gpu-restore/vast-gpu/setup.sh -o /tmp/setup.sh"
                " && bash /tmp/setup.sh > /tmp/setup.log 2>&1"
            )
            DEPLOYING["msg"] = f"sewa {offer.get('gpu_name')} ${offer.get('dph_total')}/jam..."
            c = await client.put(
                f"{VAST_API}/asks/{offer['id']}/",
                json={
                    "image": "pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime",
                    "disk": 40,
                    "env": f"-e FJ_TOKEN={token} -e FJ_BRANCH=vast/gpu-restore",
                    "onstart": onstart,
                },
                headers=_vast_headers(),
            )
            j = c.json()
            if not j.get("success"):
                DEPLOYING["msg"] = f"sewa gagal: {j}"
                return
            iid = j["new_contract"]
            _vast_save({"instance_id": iid, "gpu_token": token, "last_used": time.time()})
            DEPLOYING["msg"] = f"instance {iid} disiapkan (±20 menit pertama kali)..."
            info = await _vast_ensure_running(client)
            DEPLOYING["msg"] = f"GPU siap di {info['endpoint']}"
            log.info("vast deploy OK %s", iid)
    except Exception as e:
        DEPLOYING["msg"] = f"deploy gagal: {e}"
        log.warning("deploy: %s", e)
    finally:
        DEPLOYING["active"] = False


@app.post("/api/vast-wake")
async def vast_wake():
    if not _vast_key():
        raise HTTPException(status_code=400, detail="API key Vast belum dipasang di VPS.")
    st = _vast_state()
    if st.get("instance_id"):
        return {"status": "exists", "instance_id": st["instance_id"], "deploy": DEPLOYING["msg"]}
    asyncio.create_task(_vast_deploy_job())
    return {"status": "deploying"}


@app.get("/api/vast-status")
def vast_status():
    st = _vast_state()
    return {"configured": bool(_vast_key()), "instance_id": st.get("instance_id"),
            "last_used": st.get("last_used"), "idle_minutes": IDLE_MINUTES,
            "deploying": DEPLOYING["active"], "deploy_msg": DEPLOYING["msg"]}


@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(_vast_watchdog())


@app.get("/api/health")
def health():
    return {"status": "ok", "vast": _vast_configured()}


app.mount("/", StaticFiles(directory="/tmp/fotojelas-v2/docs/fotojelas-v2", html=True), name="web")
