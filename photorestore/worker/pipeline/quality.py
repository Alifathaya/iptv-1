"""Quality analysis Phase 2: + jumlah/ukuran wajah (Haar kasar) + artefak blok
+ rekomendasi pipeline. Skor 0-100, cost-aware."""
import os

import cv2
import numpy as np

from .base import Stage, StageResult

CASCADE = os.getenv("FACE_CASCADE_PATH",
                    "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml")


def blur_score(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def noise_estimate(gray: np.ndarray) -> float:
    h = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float64)
    sigma = np.abs(cv2.filter2D(gray.astype(np.float64), -1, h)).mean()
    return float(sigma * 0.5)


def block_artifact(gray: np.ndarray) -> float:
    """Diskontinuitas di garis kelipatan 8px (ciri kompresi JPEG). 0 = bersih."""
    g = gray.astype(np.float64)
    h, w = g.shape
    bx = np.abs(np.diff(g[:, 7::8], axis=1)).mean() if w > 16 else 0.0
    by = np.abs(np.diff(g[7::8, :], axis=0)).mean() if h > 16 else 0.0
    inner = (np.abs(np.diff(g, axis=1)).mean() + np.abs(np.diff(g, axis=0)).mean()) / 2
    return float(max(0.0, (bx + by) / 2 - inner))


_face_detector = None


def count_faces(gray: np.ndarray):
    global _face_detector
    if _face_detector is None:
        if not os.path.exists(CASCADE):
            return 0, []
        _face_detector = cv2.CascadeClassifier(CASCADE)
    small = gray if max(gray.shape) < 800 else cv2.resize(
        gray, None, fx=800 / max(gray.shape), fy=800 / max(gray.shape))
    faces = _face_detector.detectMultiScale(small, 1.1, 4)
    s = max(gray.shape) / max(small.shape)
    boxes = [[int(x * s), int(y * s), int(w * s), int(h * s)] for (x, y, w, h) in faces]
    return len(boxes), boxes


class QualityAnalysis(Stage):
    name = "quality"

    def run(self, image, ctx):
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = float(gray.mean())
        contrast = float(gray.std())
        blur = blur_score(gray)
        noise = noise_estimate(gray)
        artifact = block_artifact(gray)
        diff_rg = float(np.abs(image.astype(int)[:, :, 0] - image.astype(int)[:, :, 1]).mean())
        diff_gb = float(np.abs(image.astype(int)[:, :, 1] - image.astype(int)[:, :, 2]).mean())
        is_gray = bool(diff_rg < 3 and diff_gb < 3)
        n_faces, boxes = count_faces(gray)

        score = 100.0
        if blur < 2000:
            score -= (2000 - blur) / 2000 * 30
        if noise > 2:
            score -= min(25, (noise - 2) * 4)
        score -= min(15, abs(brightness - 128) / 128 * 15)
        if contrast < 50:
            score -= (50 - contrast) / 50 * 10
        score -= min(10, artifact * 2)
        mp = (h * w) / 1e6
        if mp < 1.0:
            score -= (1.0 - mp) * 20
        score = round(max(0, min(100, score)), 1)

        suggest = "basic" if score > 80 else ("hd" if score >= 50 else "heavy")
        notes = {"score": score, "w": w, "h": h, "mp": round(mp, 2),
                 "blur": round(blur, 1), "noise": round(noise, 2),
                 "artifact": round(artifact, 2),
                 "brightness": round(brightness, 1), "contrast": round(contrast, 1),
                 "grayscale": is_gray, "faces": n_faces,
                 "face_boxes": boxes, "suggest": suggest}
        ctx["quality"] = notes
        return StageResult(image, notes)
