"""Face restoration modular. Backend GFPGAN (bila torch+GPU) atau klasik CPU.
Fidelity 0.7-0.9: identitas dulu. Confidence rendah -> polish ringan saja."""
import os

import cv2
import numpy as np

from .base import Stage, StageResult

CONFIDENT = float(os.getenv("FACE_CONFIDENT_SCORE", "0.75"))
GFPGAN_WEIGHTS = os.getenv("GFPGAN_WEIGHTS", "/opt/restore/weights/GFPGANv1.4.pth")


def _expand(box, w, h, f=0.25):
    x, y, bw, bh = box
    nx, ny = int(x - bw * f), int(y - bh * f)
    nw, nh = int(bw * (1 + 2 * f)), int(bh * (1 + 2 * f))
    nx, ny = max(0, nx), max(0, ny)
    nw, nh = min(w - nx, nw), min(h - ny, nh)
    return nx, ny, nw, nh


def _seamless(base, patch, x, y, w, h):
    mask = np.full((h, w), 255, np.uint8)
    cx, cy = x + w // 2, y + h // 2
    try:
        return cv2.seamlessClone(patch, base, mask, (cx, cy), cv2.NORMAL_CLONE)
    except cv2.error:
        out = base.copy()
        out[y:y + h, x:x + w] = patch
        return out


class GfpganBackend:
    name = "gfpgan"
    _restorer = None

    def available(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available() and os.path.exists(GFPGAN_WEIGHTS)
        except ImportError:
            return False

    def restore(self, face: np.ndarray, fidelity: float) -> np.ndarray:
        from gfpgan import GFPGANer

        if self._restorer is None:
            self._restorer = GFPGANer(model_path=GFPGAN_WEIGHTS, upscale=1,
                                      arch="clean", channel_multiplier=2, bg_upsampler=None)
        _, _, out = self._restorer.enhance(face, has_aligned=False, only_center_face=True,
                                           paste_back=True, weight=fidelity)
        return out


class ClassicalBackend:
    """CPU konservatif: denoise + kontras lokal + tajam ringan per crop wajah."""
    name = "classical"

    def available(self) -> bool:
        return True

    def restore(self, face: np.ndarray, fidelity: float) -> np.ndarray:
        k = max(0.3, min(1.0, fidelity))
        out = cv2.bilateralFilter(face, 5, 30, 30)
        lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        out = cv2.cvtColor(cv2.merge([cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(l), a, b]),
                           cv2.COLOR_LAB2BGR)
        blur = cv2.GaussianBlur(out, (0, 0), 1.0)
        return cv2.addWeighted(out, 1.0 + 0.4 * k, blur, -0.4 * k, 0)


class FaceRestore(Stage):
    name = "face_restore"

    def __init__(self):
        gf = GfpganBackend()
        self.backend = gf if gf.available() else ClassicalBackend()

    def run(self, image: np.ndarray, ctx: dict) -> StageResult:
        fidelity = float(ctx.get("fidelity", 0.8))
        fidelity = max(0.7, min(0.9, fidelity))
        h, w = image.shape[:2]
        out = image
        done, skipped = 0, 0
        for f in ctx.get("faces", []):
            x, y, bw, bh = _expand(f["box"], w, h)
            crop = out[y:y + bh, x:x + bw].copy()
            if crop.size == 0:
                skipped += 1
                continue
            if f["score"] < CONFIDENT:
                # tidak agresif: tajam sangat ringan saja
                blur = cv2.GaussianBlur(crop, (0, 0), 1.0)
                patch = cv2.addWeighted(crop, 1.1, blur, -0.1, 0)
                skipped += 1
            else:
                patch = self.backend.restore(crop, fidelity)
                done += 1
            out = _seamless(out, patch, x, y, bw, bh)
        return StageResult(out, {"backend": self.backend.name, "restored": done,
                                 "light_only": skipped, "fidelity": fidelity})
