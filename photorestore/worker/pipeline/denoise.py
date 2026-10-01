"""Denoise adaptif: dilewati bila noise rendah (hemat), fastNlMeans bila perlu."""
import cv2
import numpy as np

from .base import Stage, StageResult

STRENGTH = {"light": 3, "medium": 6, "strong": 10}


class Denoise(Stage):
    name = "denoise"

    def run(self, image: np.ndarray, ctx: dict) -> StageResult:
        noise = ctx.get("quality", {}).get("noise", 5.0)
        if noise < 2.5:
            return StageResult(image, {"skipped": True, "reason": "noise rendah"})
        h = STRENGTH.get(ctx.get("strength", "medium"), 6)
        if max(image.shape[:2]) > 1600:
            out = cv2.bilateralFilter(image, 5, 40, 40)  # cepat untuk besar
            method = "bilateral"
        else:
            out = cv2.fastNlMeansDenoisingColored(image, None, h, h, 7, 21)
            method = "nlmeans"
        return StageResult(out, {"skipped": False, "method": method, "h": h})
