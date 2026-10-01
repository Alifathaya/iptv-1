"""Deblurring modular: DeblurProcessor.process(image, strength).
Backend klasik Richardson-Lucy FFT (light/medium/strong); backend AI
(Restormer/NAFNet) tinggal tambah class tanpa ubah backend."""
import numpy as np

from .base import Stage, StageResult


def _gaussian_psf(ksize: int, sigma: float) -> np.ndarray:
    ax = np.arange(ksize) - ksize // 2
    xx, yy = np.meshgrid(ax, ax)
    psf = np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma ** 2))
    return psf / psf.sum()


def _rl_deconv(channel: np.ndarray, psf: np.ndarray, iterations: int) -> np.ndarray:
    from numpy.fft import fft2, ifft2

    img = channel.astype(np.float64) + 1.0
    est = img.copy()
    h, w = img.shape
    H = fft2(psf, s=(h, w))
    Hc = np.conj(H)
    eps = 1e-6
    for _ in range(iterations):
        conv = np.real(ifft2(fft2(est) * H))
        rel = img / np.maximum(conv, eps)
        corr = np.real(ifft2(fft2(rel) * Hc))
        est = np.clip(est * corr, 0, 255)
    return (est - 1.0).clip(0, 255)


class ClassicalRL:
    """Richardson-Lucy FFT. Jujur: kuat untuk blur ringan-sedang,
    blur gerakan berat butuh backend AI (Phase 6 / GPU)."""
    name = "rl-fft"
    PARAMS = {"light": (5, 1.0, 5), "medium": (9, 2.0, 10), "strong": (15, 3.0, 15)}

    def process(self, image: np.ndarray, strength: str) -> np.ndarray:
        import cv2

        k, sigma, iters = self.PARAMS.get(strength, self.PARAMS["medium"])
        psf = _gaussian_psf(k, sigma)
        chs = []
        for c in cv2.split(image):
            h, w = c.shape
            scale = 1.0
            if max(h, w) > 1600:  # batasi biaya FFT di CPU
                scale = 1600 / max(h, w)
                small = cv2.resize(c, (int(w * scale), int(h * scale)))
                dec = _rl_deconv(small, psf, iters)
                chs.append(cv2.resize(dec, (w, h)).astype(np.uint8))
            else:
                chs.append(_rl_deconv(c, psf, iters).astype(np.uint8))
        return cv2.merge(chs)


class DeblurProcessor(Stage):
    name = "deblur"

    def __init__(self):
        self.backend = ClassicalRL()  # backend AI: tambah di sini bila ada

    def process(self, image, strength: str):
        return self.backend.process(image, strength)

    def run(self, image: np.ndarray, ctx: dict) -> StageResult:
        strength = ctx.get("deblur_strength", ctx.get("strength", "medium"))
        if strength not in ("light", "medium", "strong"):
            strength = "medium"
        try:
            from .remote import enabled, run_stage
            if enabled():
                out = run_stage("deblur", image, {"strength": strength})
                return StageResult(out, {"backend": "remote", "strength": strength})
        except Exception as e:
            print("remote deblur gagal, fallback lokal:", e)
        out = self.process(image, strength)
        return StageResult(out, {"backend": self.backend.name, "strength": strength})
