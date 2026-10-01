"""Basic enhancement (Phase 1, CPU): denoise ringan + kontras + tajam + upscale 2x.

Cost-aware: skor > 80 hanya dapat polish ringan + upscale (hemat waktu).
"""
import cv2
import numpy as np

from .base import Stage, StageResult

STRENGTH = {"light": 0.4, "medium": 0.7, "strong": 1.0}


class BasicEnhance(Stage):
    name = "basic"

    def run(self, image: np.ndarray, ctx: dict) -> StageResult:
        q = ctx.get("quality", {})
        score = q.get("score", 50)
        k = STRENGTH.get(ctx.get("strength", "medium"), 0.7)
        h, w = image.shape[:2]
        stages = []

        out = image
        if score <= 80:
            # denoise ringan saja di Phase 1 (model AI menyusul Phase 2)
            out = cv2.bilateralFilter(out, 5, 40 * k, 40 * k)
            stages.append("denoise-light")
        # CLAHE ringan di channel L (hindari oversaturasi: hanya luminance)
        lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.0 + k, tileGridSize=(8, 8))
        lab = cv2.merge([clahe.apply(l), a, b])
        out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        stages.append("contrast")
        # unsharp mask moderat
        blur = cv2.GaussianBlur(out, (0, 0), 1.2)
        out = cv2.addWeighted(out, 1.0 + 0.5 * k, blur, -0.5 * k, 0)
        stages.append("sharpen")
        # upscale 2x Lanczos (Real-ESRGAN menyusul Phase 2)
        out = cv2.resize(out, (w * 2, h * 2), interpolation=cv2.INTER_LANCZOS4)
        stages.append("upscale-2x")
        return StageResult(out, {"stages": stages, "strength": ctx.get("strength")})
