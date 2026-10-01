"""Unit test Phase 2: foto tajam harus skor > foto buram; rekomendasi pipeline benar."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

import cv2
import numpy as np

from pipeline.quality import QualityAnalysis
from pipeline.upscale import pick_scale

fails = []


def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name, info)
    if not cond:
        fails.append(name)


rng = np.random.default_rng(3)
base = np.full((480, 640, 3), 200, np.uint8)
cv2.circle(base, (320, 200), 90, (232, 190, 150), -1)
cv2.putText(base, "TEST", (200, 400), cv2.FONT_HERSHEY_SIMPLEX, 3, (20, 20, 20), 5)
sharp = base.copy()
blurry = cv2.GaussianBlur(base, (31, 31), 0)

qa = QualityAnalysis()
s_sharp = qa.run(sharp, {}).notes
s_blur = qa.run(blurry, {}).notes
check("skor tajam > buram", s_sharp["score"] > s_blur["score"],
      f"{s_sharp['score']} vs {s_blur['score']}")
check("suggest valid", s_sharp["suggest"] in ("basic", "hd", "heavy"), s_sharp["suggest"])
check("ada metrik artifact+faces", "artifact" in s_blur and "faces" in s_blur, "")
check("aturan upscale kecil=4x", pick_scale(800) == 4, pick_scale(800))
check("aturan upscale besar=2x", pick_scale(2500) == 2, pick_scale(2500))

print("GAGAL:" if fails else "SEMUA LOLOS", fails)
sys.exit(1 if fails else 0)
