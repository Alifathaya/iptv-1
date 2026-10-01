"""Unit test Phase 6: provider lokal jalan tanpa key; seleksi auto benar."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

import cv2
import numpy as np

from pipeline.providers import LocalAIProvider, OpenAIProvider, get_provider

fails = []


def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name, info)
    if not cond:
        fails.append(name)


img = np.full((120, 120, 3), 180, np.uint8)
cv2.line(img, (10, 10), (110, 110), (10, 10, 10), 2)  # goresan diagonal

loc = LocalAIProvider()
out, notes = loc.process(img, "abaikan")
check("local tersedia", loc.available(), "")
check("local deteksi kerusakan", notes.get("damaged_pct", 0) > 0, notes)
check("local keluaran valid", out.shape == img.shape, out.shape)

op = OpenAIProvider()
if os.getenv("OPENAI_API_KEY"):
    check("openai tersedia (ada key)", op.available(), "")
else:
    check("openai nonaktif tanpa key", not op.available(), "")

sel = get_provider("auto")
check("auto tanpa key -> lokal", sel.name == "local-inpaint", sel.name)
check("paksa lokal", get_provider("local").name == "local-inpaint", "")

print("GAGAL:" if fails else "SEMUA LOLOS", fails)
sys.exit(1 if fails else 0)
