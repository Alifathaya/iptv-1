"""Color enhancement: white balance gray-world + exposure/gamma + saturasi
dibatasi + kulit dilindungi masker YCrCb. Tanpa oversaturasi."""
import cv2
import numpy as np

from .base import Stage, StageResult


def _skin_mask(bgr: np.ndarray) -> np.ndarray:
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    cr, cb = ycrcb[:, :, 1], ycrcb[:, :, 2]
    return ((cr > 135) & (cr < 180) & (cb > 77) & (cb < 127)).astype(np.float32)


class ColorEnhance(Stage):
    name = "color"

    def run(self, image: np.ndarray, ctx: dict) -> StageResult:
        out = image.astype(np.float32)
        # gray-world white balance, dibatasi +-15%
        means = [out[:, :, c].mean() for c in range(3)]
        avg = sum(means) / 3
        for c in range(3):
            if means[c] > 1:
                out[:, :, c] *= min(1.15, max(0.85, avg / means[c]))
        # exposure: target brightness ~128 via gamma
        bright = float(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).mean())
        if bright > 1:
            gamma = np.log(128.0) / np.log(max(bright, 2.0))
            gamma = float(min(1.25, max(0.8, gamma)))
            out = 255.0 * np.power(np.clip(out / 255.0, 0, 1), gamma)
        else:
            gamma = 1.0
        out = np.clip(out, 0, 255).astype(np.uint8)
        # saturasi +10% kecuali area kulit
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
        skin = _skin_mask(out)
        boost = np.ones_like(skin) * 1.1
        boost[skin > 0] = 1.0
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * boost, 0, 255)
        out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        return StageResult(out, {"gamma": round(gamma, 3)})
