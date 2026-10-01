"""Upscale modular: Lanczos (selalu tersedia) atau Real-ESRGAN (bila
USE_REALESRGAN=1 + torch + GPU). Aturan skala configurable via env."""
import os

import cv2
import numpy as np

from .base import Stage, StageResult

SMALL_PX = int(os.getenv("UPSCALE_SMALL_PX", "1000"))
LARGE_PX = int(os.getenv("UPSCALE_LARGE_PX", "2000"))
USE_REALESRGAN = os.getenv("USE_REALESRGAN", "false").lower() == "true"


def pick_scale(max_side: int) -> int:
    if max_side > LARGE_PX:
        return 2
    if max_side < SMALL_PX:
        return 4
    return 2


class LanczosUpscaler:
    name = "lanczos"

    def upscale(self, image: np.ndarray, scale: int) -> np.ndarray:
        h, w = image.shape[:2]
        return cv2.resize(image, (w * scale, h * scale), interpolation=cv2.INTER_LANCZOS4)


class RealEsrganUpscaler:
    name = "realesrgan"
    _model = None

    def _load(self):
        if self._model is not None:
            return self._model
        import torch
        from basicsr.utils.download_util import load_file_from_url
        from realesrgan import RealESRGANer
        from basicsr.archs.rrdbnet_arch import RRDBNet

        half = torch.cuda.is_available()
        wdir = os.getenv("MODEL_DIR", "/opt/restore/weights")
        os.makedirs(wdir, exist_ok=True)
        path = load_file_from_url(
            "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth", wdir)
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                        num_block=23, num_grow_ch=32, scale=4)
        self._model = RealESRGANer(scale=4, model_path=path, model=model,
                                   tile=400, tile_pad=10, pre_pad=0, half=half)
        return self._model

    def upscale(self, image: np.ndarray, scale: int) -> np.ndarray:
        out, _ = self._load().enhance(image, outscale=scale)
        return out


class Upscale(Stage):
    name = "upscale"

    def __init__(self):
        if USE_REALESRGAN:
            try:
                self.backend = RealEsrganUpscaler()
                self.backend._load()
            except Exception as e:
                print("Real-ESRGAN tidak aktif, fallback Lanczos:", e)
                self.backend = LanczosUpscaler()
        else:
            self.backend = LanczosUpscaler()

    def run(self, image: np.ndarray, ctx: dict) -> StageResult:
        scale = ctx.get("force_scale") or pick_scale(max(image.shape[:2]))
        try:
            from .remote import enabled, run_stage
            if enabled():
                out = run_stage("upscale", image, {"scale": scale})
                ctx["expected_scale"] = scale
                return StageResult(out, {"backend": "realesrgan-remote", "scale": scale})
        except Exception as e:
            print("remote upscale gagal, fallback lokal:", e)
        out = self.backend.upscale(image, scale)
        ctx["expected_scale"] = scale
        return StageResult(out, {"backend": self.backend.name, "scale": scale})
