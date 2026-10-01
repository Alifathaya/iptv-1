"""Quality analysis: metrik + skor 0-100 untuk memilih pipeline (cost-aware)."""
import cv2
import numpy as np

from .base import Stage, StageResult


def blur_score(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def noise_estimate(gray: np.ndarray) -> float:
    h = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float64)
    sigma = np.abs(cv2.filter2D(gray.astype(np.float64), -1, h)).mean()
    return float(sigma * 0.5)


class QualityAnalysis(Stage):
    name = "quality"

    def run(self, image: np.ndarray, ctx: dict) -> StageResult:
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = float(gray.mean())
        contrast = float(gray.std())
        blur = blur_score(gray)
        noise = noise_estimate(gray)
        diff_rg = float(np.abs(image.astype(int)[:, :, 0] - image.astype(int)[:, :, 1]).mean())
        diff_gb = float(np.abs(image.astype(int)[:, :, 1] - image.astype(int)[:, :, 2]).mean())
        is_gray = bool(diff_rg < 3 and diff_gb < 3)

        score = 100.0
        score -= max(0, min(30, (2000 - blur) / 2000 * 30)) if blur < 2000 else 0
        score -= max(0, min(25, (noise - 2) * 4)) if noise > 2 else 0
        score -= max(0, min(15, abs(brightness - 128) / 128 * 15))
        score -= max(0, min(10, (50 - contrast) / 50 * 10)) if contrast < 50 else 0
        mp = (h * w) / 1e6
        if mp < 1.0:
            score -= (1.0 - mp) * 20
        score = round(max(0, min(100, score)), 1)

        notes = {"score": score, "w": w, "h": h, "mp": round(mp, 2),
                 "blur": round(blur, 1), "noise": round(noise, 2),
                 "brightness": round(brightness, 1), "contrast": round(contrast, 1),
                 "grayscale": is_gray}
        ctx["quality"] = notes
        return StageResult(image, notes)
