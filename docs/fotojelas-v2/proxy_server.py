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
STOP_AFTER_MIN = 30  # cadangan: stop bila stop-utama gagal (instance RUNNING)
DESTROY_AFTER_DAYS = 7  # destroy bila tak tersentuh 7 hari -> nol total
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
        vast = _vast_configured()
        if req.mode == "enhance":
            if vast:
                try:
                    b64 = await _vast_stage(client, "enhance", req.image,
                                            req.fidelity, req.upscale)
                    return {"image_b64": b64, "provider": "vast-gpu"}
                except HTTPException:
                    raise
                except Exception as e:
                    log.warning("vast gagal, fallback fal: %s", e)
            key = (x_fal_key or "").strip()
            if not key:
                raise HTTPException(status_code=400, detail="Key fal.ai kosong (dan GPU Vast belum aktif).")
            inp = {"image_url": req.image, "fidelity": req.fidelity,
                   "upscale_factor": req.upscale, "face_upscale": True}
            inp.update(req.extra)
            url = await _run(client, key, req.model_enhance, inp, "enhance")
        elif req.mode == "colorize":
            if vast:
                try:
                    b64 = await _vast_stage(client, "colorize", req.image,
                                            req.fidelity, req.upscale)
                    return {"image_b64": b64, "provider": "vast-gpu"}
                except HTTPException:
                    raise
                except Exception as e:
                    log.warning("vast gagal, fallback fal: %s", e)
            key = (x_fal_key or "").strip()
            if not key:
                raise HTTPException(status_code=400, detail="Key fal.ai kosong (dan GPU Vast belum aktif).")
            inp = {"image_url": req.image}
            inp.update(req.extra)
            url = await _run(client, key, req.model_colorize, inp, "colorize")
        else:
            if vast:
                try:
                    colored = await _vast_stage(client, "colorize", req.image,
                                                req.fidelity, req.upscale)
                    b64 = await _vast_stage(client, "enhance", colored,
                                            req.fidelity, req.upscale)
                    return {"image_b64": b64, "provider": "vast-gpu"}
                except HTTPException:
                    raise
                except Exception as e:
                    log.warning("vast gagal, fallback fal: %s", e)
            key = (x_fal_key or "").strip()
            if not key:
                raise HTTPException(status_code=400, detail="Key fal.ai kosong (dan GPU Vast belum aktif).")
            inp1 = {"image_url": req.image}
            inp1.update((req.extra or {}).get("colorize", {}))
            colored = await _run(client, key, req.model_colorize, inp1, "full-1-colorize")
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
    r = await client.get(f"{VAST_API}/instances/{iid}/", headers=_vast_headers())
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
        r = await client.put(f"{VAST_API}/instances/{iid}/", json={"state": "running"}, headers=_vast_headers())
        if not r.json().get("success", True):
            raise RuntimeError(f"start gagal: {r.text[:200]}")
        t0 = time.time()
        while time.time() - t0 < 1500:
            await asyncio.sleep(20)
            inst = await _vast_instance(client, iid)
            status = inst.get("actual_status")
            if status == "running":
                break
            msg = str(inst.get("status_msg") or "")
            if "failed to start" in msg or "CDI" in msg or "OCI runtime" in msg:
                raise RuntimeError(f"host rusak ({msg[:120]}), ganti host")
            if status in ("exited", "unknown", "offline"):
                raise RuntimeError(f"instance {status}, hubungi admin")
        else:
            raise RuntimeError("instance tidak running dalam 25 menit")
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
    st["busy"] = True  # kunci: watchdog tidak boleh destroy saat job jalan
    _vast_save(st)
    return {"endpoint": ep, "token": st.get("gpu_token", "")}


async def _vast_stop(client: httpx.AsyncClient, iid: int) -> None:
    try:
        await client.put(f"{VAST_API}/instances/{iid}/", json={"state": "stopped"}, headers=_vast_headers())
        log.info("vast %s stopped sehabis 1 foto (start lagi ±1 mnt)", iid)
    except Exception as e:
        log.warning("stop %s gagal: %s", iid, e)
    st = _vast_state()
    st["last_used"] = time.time()  # watchdog dihitung dari SELESAI
    st["busy"] = False
    _vast_save(st)


async def _vast_destroy(client: httpx.AsyncClient, iid: int) -> None:
    try:
        await client.delete(f"{VAST_API}/instances/{iid}/", headers=_vast_headers())
        log.info("vast %s destroyed (nganggur %s hari)", iid, DESTROY_AFTER_DAYS)
    except Exception as e:
        log.warning("destroy %s gagal: %s", iid, e)
    st = _vast_state()
    st.pop("instance_id", None)
    st["last_used"] = 0
    _vast_save(st)


async def _vast_stage(client: httpx.AsyncClient, kind: str, image: str,
                      fidelity: float, upscale: int) -> str:
    """kind enhance -> GPU /v1/restore ; kind colorize -> GPU /v1/stage."""
    info = await _vast_ensure_running(client)
    try:
        if kind == "enhance":
            r = await client.post(
                info["endpoint"] + "/v1/restore",
                json={"image": image, "fidelity": fidelity, "upscale": upscale},
                headers={"X-Api-Token": info["token"]},
                timeout=600,
            )
        else:
            r = await client.post(
                info["endpoint"] + "/v1/stage",
                json={"stage": "colorize", "image": image, "params": {}},
                headers={"X-Api-Token": info["token"]},
                timeout=600,
            )
        if r.status_code != 200:
            raise RuntimeError(f"gpu {r.status_code}: {r.text[:300]}")
        b64 = r.json().get("image_b64")
        if not b64:
            raise RuntimeError("gpu hasil kosong")
    finally:
        st = _vast_state()
        st["busy"] = False
        st["last_used"] = time.time()  # watchdog dihitung dari SELESAI
        _vast_save(st)
    # hasil sudah di tangan -> stop langsung (start lagi ±1 mnt);
    # destroy hanya bila 7 hari tak tersentuh (watchdog)
    st = _vast_state()
    if st.get("instance_id"):
        await _vast_stop(client, st["instance_id"])
    return b64


async def _vast_watchdog() -> None:
    while True:
        await asyncio.sleep(60)
        try:
            st = _vast_state()
            iid = st.get("instance_id")
            last = st.get("last_used", 0)
            if not iid or st.get("busy") or not last:
                continue
            idle = time.time() - last
            async with httpx.AsyncClient(timeout=30) as client:
                inst = await _vast_instance(client, iid)
                status = inst.get("actual_status")
                if status == "running" and idle > STOP_AFTER_MIN * 60:
                    # stop-utama gagal / dinyalakan manual -> stop paksa
                    await client.put(f"{VAST_API}/instances/{iid}/", json={"state": "stopped"},
                                     headers=_vast_headers())
                    log.info("watchdog stop %s (nganggur)", iid)
                elif status != "running" and idle > DESTROY_AFTER_DAYS * 86400:
                    await _vast_destroy(client, iid)
        except Exception as e:
            log.warning("watchdog: %s", e)


def _pick_offers(offers: list, bad_hosts: set) -> list:
    cands = []
    for o in offers:
        if not o.get("rentable"):
            continue
        if (o.get("disk_space") or 0) < 40:
            continue
        if o.get("host_id") in bad_hosts:
            continue
        name = str(o.get("gpu_name", ""))
        if "3090" not in name and "4090" not in name and "A5000" not in name \
                and "A4000" not in name and "A4500" not in name:
            continue
        if (o.get("reliability2") or 0) < 0.95:
            continue
        if (o.get("cuda_max_good") or 0) < 12.0:
            continue
        cands.append(o)
    cands.sort(key=lambda o: o.get("dph_total", 9e9))
    return cands[:3]


def _pick_offer(offers: list) -> dict:
    st = _vast_state()
    c = _pick_offers(offers, set(st.get("bad_hosts", [])))
    return c[0] if c else {}


async def _vast_deploy_job() -> None:
    if DEPLOYING["active"]:
        return
    DEPLOYING.update(active=True, msg="mencari GPU termurah...")
    try:
        import secrets

        async with httpx.AsyncClient(timeout=60) as client:
            q = {"order": [["dph_total", "asc"]], "limit": 200}
            import urllib.parse

            r = await client.get(
                f"{VAST_API}/bundles/?q={urllib.parse.quote_plus(__import__('json').dumps(q))}",
                headers=_vast_headers(),
            )
            offers = (r.json().get("offers") or []) if r.status_code == 200 else []
            st0 = _vast_state()
            cands = _pick_offers(offers, set(st0.get("bad_hosts", [])))
            if not cands:
                DEPLOYING["msg"] = "tidak ada offer GPU yang cocok saat ini"
                return
            token = secrets.token_hex(16)
            image = "ghcr.io/alifathaya/fotojelas-gpu:3"
            body = {"image": image, "disk": 30,
                    "env": f"-e FJ_TOKEN={token}"}
            try:
                with open(os.path.expanduser("~/.github-packages-token")) as f:
                    ght = f.read().strip()
                if ght:
                    body["image_login"] = f"-u Alifathaya -p {ght} ghcr.io"
            except OSError:
                pass
            last_err = "tidak ada kandidat"
            for offer in cands:
                DEPLOYING["msg"] = f"sewa {offer.get('gpu_name')} ${offer.get('dph_total')}/jam..."
                c = await client.put(
                    f"{VAST_API}/asks/{offer['id']}/", json=body, headers=_vast_headers(),
                )
                j = c.json()
                if not j.get("success"):
                    last_err = f"sewa gagal: {j}"
                    continue
                iid = j["new_contract"]
                _vast_save({"instance_id": iid, "gpu_token": token, "last_used": 0,
                            "busy": False, "bad_hosts": st0.get("bad_hosts", [])})
                DEPLOYING["msg"] = f"instance {iid} disiapkan (±15 menit pertama)..."
                try:
                    info = await _vast_ensure_running(client)
                except Exception as e:
                    # host rusak -> blacklist + hapus yatim + coba host lain
                    last_err = str(e)
                    try:
                        bh = set(_vast_state().get("bad_hosts", []))
                        if offer.get("host_id"):
                            bh.add(offer["host_id"])
                        _vast_save({"bad_hosts": sorted(bh)})
                        async with httpx.AsyncClient(timeout=30) as c2:
                            await c2.delete(f"{VAST_API}/instances/{iid}/", headers=_vast_headers())
                    except Exception:
                        pass
                    DEPLOYING["msg"] = f"host bermasalah, coba host lain... ({last_err[:80]})"
                    continue
                DEPLOYING["msg"] = f"GPU siap di {info['endpoint']}"
                log.info("vast deploy OK %s", iid)
                break
            else:
                DEPLOYING["msg"] = f"deploy gagal: {last_err}"
                log.warning("deploy: %s", last_err)
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
            "last_used": st.get("last_used"), "stop_after_min": STOP_AFTER_MIN,
            "destroy_after_days": DESTROY_AFTER_DAYS,
            "deploying": DEPLOYING["active"], "deploy_msg": DEPLOYING["msg"]}


@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(_vast_watchdog())


@app.get("/api/health")
def health():
    return {"status": "ok", "vast": _vast_configured()}


app.mount("/", StaticFiles(directory="/tmp/fotojelas-v2/docs/fotojelas-v2", html=True), name="web")
