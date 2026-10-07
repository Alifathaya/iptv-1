"""AI Worker GPU — Flux soft-restore path (tag :flux1).
Replaces oversaturated DDColor+CodeFormer default with FLUX.1-schnell img2img.
Mask strategy: FULL-IMAGE soft restore (strength < 1). No Fill mask — Fill-dev
is HF-gated and no token is available on Contabo. Damage speckles get a light
Telea pre-pass only.
"""
import base64
import logging
import os
import threading
import time

import cv2
import numpy as np
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gpuworker")

TOKEN = os.getenv("FJ_TOKEN", "")
MODEL_ID = os.getenv("FLUX_MODEL_ID", "black-forest-labs/FLUX.1-schnell")
HF_HOME = os.getenv("HF_HOME", "/opt/restore/hf")
os.environ.setdefault("HF_HOME", HF_HOME)
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", os.path.join(HF_HOME, "hub"))

app = FastAPI(title="FotoRestore GPU worker (Flux)")

_flux_pipe = None
_flux_lock = threading.Lock()
_flux_meta = {"loaded": False, "model": MODEL_ID, "mode": None, "vram_peak_gb": None}


class StageReq(BaseModel):
    stage: str
    image: str  # dataURL
    params: dict = {}


class RestoreReq(BaseModel):
    image: str
    strength: float = 0.42
    steps: int = 4
    repair: bool = True
    repair_strength: str = "medium"
    max_side: int = 768
    sharpen: bool = True


def _img(data_url: str):
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    img = cv2.imdecode(np.frombuffer(base64.b64decode(b64), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="gambar tidak valid")
    return img


def _out(img) -> str:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise HTTPException(status_code=500, detail="encode gagal")
    return "data:image/png;base64," + base64.b64encode(bytes(buf)).decode()


def _round16(n: int) -> int:
    return max(64, int(round(n / 16.0)) * 16)


def _resize_for_flux(img, max_side=768):
    h, w = img.shape[:2]
    scale = float(max_side) / float(max(h, w))
    if scale < 1.0:
        nh, nw = _round16(h * scale), _round16(w * scale)
    else:
        # Slight upscale of small inputs for better Flux detail; cap 1.5x
        up = min(1.5, float(max_side) / float(max(h, w)))
        nh, nw = _round16(h * up), _round16(w * up)
    if (nh, nw) != (h, w):
        img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    return img


def _detect_damage_mask(gray, strength="medium"):
    thr = {"light": 235, "medium": 225, "strong": 210}.get(strength, 225)
    bright = (gray >= thr).astype(np.uint8) * 255
    dark = (gray <= (15 if strength != "strong" else 25)).astype(np.uint8) * 255
    mask = cv2.bitwise_or(bright, dark)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
    mask = cv2.dilate(mask, k, iterations=1)
    return mask


def _telea_residual(img, strength="medium"):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = _detect_damage_mask(gray, strength)
    if int(mask.sum()) == 0:
        return img
    return cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)


def _do_repair(img, strength="medium"):
    """Light classical cleanup only (no DDColor/zeroscratches in Flux image)."""
    try:
        out = _telea_residual(img, strength)
        log.info("telea repair strength=%s", strength)
        return out
    except Exception as e:
        log.warning("repair skip: %s", e)
        return img


def _light_sharpen(img, amount=0.28, radius=0.9):
    blur = cv2.GaussianBlur(img, (0, 0), radius)
    return cv2.addWeighted(img, 1.0 + amount, blur, -amount, 0)


def _load_flux():
    """Lazy-load FLUX.1-schnell img2img with NF4 when possible, else bf16+offload."""
    global _flux_pipe
    if _flux_pipe is not None:
        return _flux_pipe
    with _flux_lock:
        if _flux_pipe is not None:
            return _flux_pipe
        import torch
        from diffusers import FluxImg2ImgPipeline

        if not torch.cuda.is_available():
            raise RuntimeError("butuh CUDA untuk Flux")

        t0 = time.time()
        log.info("loading Flux model %s ...", MODEL_ID)
        mode = "bf16_offload"
        pipe = None
        try:
            from diffusers import BitsAndBytesConfig as DiffusersBitsAndBytesConfig
            from diffusers import FluxTransformer2DModel
            from transformers import BitsAndBytesConfig as TransformersBitsAndBytesConfig
            from transformers import T5EncoderModel

            bnb_t5 = TransformersBitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
            )
            bnb_tr = DiffusersBitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
            )
            text_encoder_2 = T5EncoderModel.from_pretrained(
                MODEL_ID,
                subfolder="text_encoder_2",
                quantization_config=bnb_t5,
                torch_dtype=torch.bfloat16,
            )
            transformer = FluxTransformer2DModel.from_pretrained(
                MODEL_ID,
                subfolder="transformer",
                quantization_config=bnb_tr,
                torch_dtype=torch.bfloat16,
            )
            pipe = FluxImg2ImgPipeline.from_pretrained(
                MODEL_ID,
                transformer=transformer,
                text_encoder_2=text_encoder_2,
                torch_dtype=torch.bfloat16,
            )
            pipe.enable_model_cpu_offload()
            mode = "nf4_offload"
            log.info("Flux NF4 load OK in %.1fs", time.time() - t0)
        except Exception as e:
            log.warning("NF4 load failed (%s); falling back to bf16+offload", e)
            pipe = FluxImg2ImgPipeline.from_pretrained(
                MODEL_ID, torch_dtype=torch.bfloat16
            )
            pipe.enable_model_cpu_offload()
            try:
                pipe.vae.enable_tiling()
                pipe.vae.enable_slicing()
            except Exception:
                pass
            mode = "bf16_offload"
            log.info("Flux bf16 load OK in %.1fs", time.time() - t0)

        _flux_pipe = pipe
        _flux_meta["loaded"] = True
        _flux_meta["mode"] = mode
        _flux_meta["model"] = MODEL_ID
        return _flux_pipe


DEFAULT_PROMPT = (
    "Restore this damaged old photograph. Remove scratches, blotches, dust, "
    "and water stains. Preserve the exact face likeness, identity, pose, and "
    "composition. Natural muted realistic skin tones and clothing colors — "
    "not oversaturated, not stylized, not illustrated. Photorealistic archival "
    "restoration, sharp but gentle detail, clean background."
)
DEFAULT_NEG = (
    "oversaturated, neon colors, cartoon, anime, painting, illustration, "
    "distorted face, extra limbs, watermark, text, blurry, plastic skin"
)


def _do_flux_restore(
    img,
    strength=0.42,
    steps=4,
    max_side=768,
    prompt=None,
    seed=42,
):
    import torch
    from PIL import Image

    pipe = _load_flux()
    src = _resize_for_flux(img, max_side=int(max_side))
    h, w = src.shape[:2]
    rgb = cv2.cvtColor(src, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)

    strength = float(max(0.15, min(0.85, strength)))
    steps = int(max(2, min(8, steps)))
    prompt = prompt or DEFAULT_PROMPT

    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    gen = torch.Generator(device="cpu").manual_seed(int(seed))
    # schnell: guidance_scale=0
    kwargs = dict(
        prompt=prompt,
        image=pil,
        strength=strength,
        num_inference_steps=steps,
        guidance_scale=0.0,
        height=h,
        width=w,
        generator=gen,
        max_sequence_length=256,
    )
    try:
        out = pipe(**kwargs).images[0]
    except TypeError:
        # older diffusers may not take max_sequence_length on img2img
        kwargs.pop("max_sequence_length", None)
        out = pipe(**kwargs).images[0]

    peak = None
    try:
        peak = round(torch.cuda.max_memory_allocated() / (1024 ** 3), 2)
        _flux_meta["vram_peak_gb"] = peak
    except Exception:
        pass
    log.info(
        "flux_restore done strength=%.2f steps=%d %dx%d in %.1fs vram_peak=%s mode=%s",
        strength, steps, w, h, time.time() - t0, peak, _flux_meta.get("mode"),
    )
    arr = np.array(out)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    return bgr


@app.get("/health")
def health():
    try:
        import torch
        cuda = torch.cuda.is_available()
        name = torch.cuda.get_device_name(0) if cuda else None
    except Exception:
        cuda = False
        name = None
    return {
        "status": "ok",
        "cuda": cuda,
        "gpu": name,
        "flux_loaded": _flux_meta["loaded"],
        "flux_mode": _flux_meta.get("mode"),
        "model": MODEL_ID,
    }


@app.post("/v1/warmup")
def warmup(x_api_token: str = Header(default="")):
    if TOKEN and x_api_token != TOKEN:
        raise HTTPException(status_code=401, detail="token salah")
    t0 = time.time()
    _load_flux()
    return {
        "ok": True,
        "secs": round(time.time() - t0, 1),
        "meta": dict(_flux_meta),
    }


@app.post("/v1/restore")
def restore(req: RestoreReq, x_api_token: str = Header(default="")):
    if TOKEN and x_api_token != TOKEN:
        raise HTTPException(status_code=401, detail="token salah")
    img = _img(req.image)
    try:
        if req.repair:
            img = _do_repair(img, req.repair_strength)
        out = _do_flux_restore(
            img,
            strength=req.strength,
            steps=req.steps,
            max_side=req.max_side,
        )
        if req.sharpen:
            out = _light_sharpen(out, amount=0.25, radius=0.8)
    except HTTPException:
        raise
    except Exception as e:
        log.exception("restore gagal")
        raise HTTPException(status_code=500, detail=f"restore gagal: {e}")
    return {
        "image_b64": _out(out),
        "meta": {
            "model": MODEL_ID,
            "mode": _flux_meta.get("mode"),
            "vram_peak_gb": _flux_meta.get("vram_peak_gb"),
            "mask_strategy": "full_image_soft_img2img",
            "strength": req.strength,
            "steps": req.steps,
        },
    }


@app.post("/v1/stage")
def stage(req: StageReq, x_api_token: str = Header(default="")):
    if TOKEN and x_api_token != TOKEN:
        raise HTTPException(status_code=401, detail="token salah")
    img = _img(req.image)
    try:
        if req.stage in ("flux_restore", "restore", "enhance", "face_restore"):
            strength = float(req.params.get("strength", 0.42))
            steps = int(req.params.get("steps", 4))
            max_side = int(req.params.get("max_side", 768))
            do_repair = bool(req.params.get("repair", True))
            prompt = req.params.get("prompt")
            if do_repair:
                img = _do_repair(img, str(req.params.get("repair_strength", "medium")))
            out = _do_flux_restore(
                img,
                strength=strength,
                steps=steps,
                max_side=max_side,
                prompt=prompt,
                seed=int(req.params.get("seed", 42)),
            )
            if bool(req.params.get("sharpen", True)):
                out = _light_sharpen(out, amount=0.25, radius=0.8)
        elif req.stage == "repair":
            out = _do_repair(img, str(req.params.get("strength", "medium")))
        elif req.stage == "sharpen":
            out = _light_sharpen(
                img,
                amount=float(req.params.get("amount", 0.35)),
                radius=float(req.params.get("radius", 1.0)),
            )
        elif req.stage == "warmup":
            _load_flux()
            return {"image_b64": _out(img), "meta": dict(_flux_meta)}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"stage {req.stage} tak dikenal (flux1: flux_restore|repair|sharpen|warmup)",
            )
    except HTTPException:
        raise
    except Exception as e:
        log.exception("stage %s gagal", req.stage)
        raise HTTPException(status_code=500, detail=f"{req.stage} gagal: {e}")
    return {
        "image_b64": _out(out),
        "meta": {
            "model": MODEL_ID,
            "mode": _flux_meta.get("mode"),
            "vram_peak_gb": _flux_meta.get("vram_peak_gb"),
            "mask_strategy": "full_image_soft_img2img",
        },
    }
