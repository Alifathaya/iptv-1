"""Buat 30 foto sintetis: 10 low + 10 medium + 10 high (PIL/numpy, tanpa download)."""
import os

import numpy as np
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(__file__), "samples")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


def face_like(w, h, quality):
    arr = np.full((h, w, 3), 210, np.uint8)
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    d.ellipse([w * .3, h * .25, w * .7, h * .65], fill=(232, 190, 150))  # wajah
    d.ellipse([w * .38, h * .38, w * .46, h * .44], fill=(30, 30, 30))  # mata
    d.ellipse([w * .54, h * .38, w * .62, h * .44], fill=(30, 30, 30))
    d.arc([w * .4, h * .5, w * .6, h * .6], 0, 180, fill=(150, 60, 60), width=3)  # mulut
    a = np.array(img).astype(np.int16)
    if quality == "low":
        a = a + rng.integers(-45, 45, a.shape)  # noise berat
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((w // 4, h // 4)).resize((w, h))
    elif quality == "medium":
        a = a + rng.integers(-15, 15, a.shape)
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return img


for i in range(10):
    face_like(640, 480, "low").save(f"{OUT}/low_{i:02d}.jpg", quality=40)      # kecil+noise+kompresi
    face_like(1280, 960, "medium").save(f"{OUT}/med_{i:02d}.jpg", quality=80)
    face_like(1920, 1440, "high").save(f"{OUT}/high_{i:02d}.jpg", quality=95)
print("OK", len(os.listdir(OUT)))
