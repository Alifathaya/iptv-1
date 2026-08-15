"""Real-ESRGAN GPU/CPU image enhancement."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
import torch
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

from .config import TILE_PAD, TILE_SIZE

logger = logging.getLogger(__name__)

WEIGHTS_DIR = Path(os.getenv("WEIGHTS_DIR", "/app/weights"))

MODEL_URLS = {
    4: "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    2: "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
}


def _device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _download_weights(scale: int) -> Path:
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = "RealESRGAN_x4plus.pth" if scale == 4 else "RealESRGAN_x2plus.pth"
    path = WEIGHTS_DIR / filename
    if path.exists():
        return path

    url = MODEL_URLS[scale]
    logger.info("Downloading model weights: %s", url)
    torch.hub.download_url_to_file(url, str(path), progress=True)
    return path


def _build_upsampler(scale: Literal[2, 4]) -> RealESRGANer:
    device = _device()
    use_half = device.type == "cuda"
    model_path = str(_download_weights(scale))

    if scale == 4:
        model = RRDBNet(
            num_in_ch=3, num_out_ch=3, num_feat=64,
            num_block=23, num_grow_ch=32, scale=4,
        )
    else:
        model = RRDBNet(
            num_in_ch=3, num_out_ch=3, num_feat=64,
            num_block=23, num_grow_ch=32, scale=2,
        )

    return RealESRGANer(
        scale=scale,
        model_path=model_path,
        model=model,
        tile=TILE_SIZE,
        tile_pad=TILE_PAD,
        pre_pad=0,
        half=use_half,
        device=device,
    )


class GpuEnhancer:
    """Lazy-loaded Real-ESRGAN pipeline with optional deblur preprocess."""

    def __init__(self) -> None:
        self._upsamplers: dict[int, RealESRGANer] = {}

    def get_upsampler(self, scale: Literal[2, 4]) -> RealESRGANer:
        if scale not in self._upsamplers:
            logger.info("Loading Real-ESRGAN %sx on %s", scale, _device())
            self._upsamplers[scale] = _build_upsampler(scale)
        return self._upsamplers[scale]

    def gpu_info(self) -> dict:
        if torch.cuda.is_available():
            return {
                "available": True,
                "name": torch.cuda.get_device_name(0),
                "cuda_version": torch.version.cuda,
                "device_count": torch.cuda.device_count(),
            }
        return {"available": False, "name": None, "cuda_version": None, "device_count": 0}

    def _preprocess_deblur(self, img: np.ndarray, strength: int) -> np.ndarray:
        if strength <= 0:
            return img

        out = img.copy()
        s = max(0, min(100, strength))

        if s >= 25:
            out = cv2.fastNlMeansDenoisingColored(out, None, 5, 5, 7, 15)

        blur = cv2.GaussianBlur(out, (0, 0), sigmaX=1.2 + s * 0.03)
        amount = 0.4 + s * 0.012
        out = cv2.addWeighted(out, 1.0 + amount, blur, -amount, 0)

        if s >= 50:
            blur2 = cv2.GaussianBlur(out, (0, 0), sigmaX=2.5)
            out = cv2.addWeighted(out, 1.15, blur2, -0.15, 0)

        return np.clip(out, 0, 255).astype(np.uint8)

    def _post_polish(self, img: np.ndarray, sharpness: int, contrast: int) -> np.ndarray:
        out = img.copy()
        s = max(0, min(100, sharpness))
        c = max(0, min(100, contrast))

        if c > 0:
            lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=1.0 + c * 0.04, tileGridSize=(8, 8))
            l = clahe.apply(l)
            out = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        if s > 0:
            blur = cv2.GaussianBlur(out, (0, 0), 1.0)
            amount = s / 100.0 * 0.8
            out = cv2.addWeighted(out, 1.0 + amount, blur, -amount, 0)

        return np.clip(out, 0, 255).astype(np.uint8)

    def enhance(
        self,
        img_bgr: np.ndarray,
        scale: Literal[4, 8] = 4,
        deblur_strength: int = 80,
        sharpness: int = 60,
        contrast: int = 25,
    ) -> np.ndarray:
        work = self._preprocess_deblur(img_bgr, deblur_strength)

        if scale == 8:
            upsampler4 = self.get_upsampler(4)
            work, _ = upsampler4.enhance(work, outscale=4)
            upsampler2 = self.get_upsampler(2)
            work, _ = upsampler2.enhance(work, outscale=2)
        else:
            upsampler4 = self.get_upsampler(4)
            work, _ = upsampler4.enhance(work, outscale=4)

        return self._post_polish(work, sharpness, contrast)


enhancer = GpuEnhancer()
