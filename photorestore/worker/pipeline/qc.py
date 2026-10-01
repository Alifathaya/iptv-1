"""Quality gate: pastikan output tidak lebih buruk dari input.
Gagal -> job failed dengan alasan jelas (user bisa ulangi dgn strength ringan)."""
import cv2

from .base import Stage, StageResult
from .quality import blur_score, noise_estimate


class QualityGate(Stage):
    name = "qc"

    def run(self, image, ctx):
        if image is None or image.size == 0:
            raise ValueError("QC: gambar output kosong")
        exp_scale = ctx.get("expected_scale", 2)
        iw, ih = ctx.get("in_wh", (image.shape[1] // exp_scale, image.shape[0] // exp_scale))
        if (image.shape[1], image.shape[0]) != (iw * exp_scale, ih * exp_scale):
            raise ValueError(f"QC: dimensi {image.shape[1]}x{image.shape[0]} != target {iw*exp_scale}x{ih*exp_scale}")
        # bandingkan pada resolusi SAMA (skor blur/noise tergantung skala)
        probe = cv2.resize(image, (iw, ih), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(probe, cv2.COLOR_BGR2GRAY)
        qin = ctx.get("quality", {})
        blur_in = qin.get("blur", 0)
        blur_out = blur_score(gray)
        noise_out = noise_estimate(gray)
        if blur_in and blur_out < blur_in * 0.5 and blur_in > 100:
            raise ValueError(f"QC: ketajaman turun drastis ({blur_in:.0f}->{blur_out:.0f})")
        if noise_out > 40:
            raise ValueError(f"QC: noise output {noise_out:.1f} terlalu tinggi")
        return StageResult(image, {"blur_in": round(blur_in, 1), "blur_out": round(blur_out, 1),
                                   "noise_out": round(noise_out, 2)})
