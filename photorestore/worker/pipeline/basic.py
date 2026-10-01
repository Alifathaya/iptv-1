"""Basic enhancement Phase 2: kontras + tajam (denoise sudah tahap sendiri)."""
import cv2
import numpy as np

from .base import Stage, StageResult

STRENGTH = {"light": 0.4, "medium": 0.7, "strong": 1.0}


class BasicEnhance(Stage):
    name = "basic"

    def run(self, image: np.ndarray, ctx: dict) -> StageResult:
        k = STRENGTH.get(ctx.get("strength", "medium"), 0.7)
        stages = []

        out = image
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
        return StageResult(out, {"stages": stages, "strength": ctx.get("strength")})
