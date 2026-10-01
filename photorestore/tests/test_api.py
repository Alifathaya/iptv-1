"""Test API: upload valid/invalid + alur job sampai completed."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import httpx

BASE = os.getenv("API_BASE", "http://127.0.0.1:8101")
SAMPLES = os.path.join(os.path.dirname(__file__), "samples")

fails = []


def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name, info)
    if not cond:
        fails.append(name)


# invalid: bukan gambar
r = httpx.post(BASE + "/api/v1/enhance", files={"file": ("x.txt", b"halo", "text/plain")})
check("tolak text/plain", r.status_code == 415, r.status_code)
# invalid: bytes rusak
r = httpx.post(BASE + "/api/v1/enhance", files={"file": ("x.jpg", b"\xff\xd8corrupt", "image/jpeg")})
check("tolak corrupt", r.status_code == 400, r.status_code)
# invalid: terlalu kecil (10x10)
from PIL import Image
import io

buf = io.BytesIO()
Image.new("RGB", (10, 10)).save(buf, "JPEG")
r = httpx.post(BASE + "/api/v1/enhance", files={"file": ("k.jpg", buf.getvalue(), "image/jpeg")})
check("tolak terlalu kecil", r.status_code == 400, r.status_code)
# invalid: mode belum ada
with open(f"{SAMPLES}/med_00.jpg", "rb") as f:
    r = httpx.post(BASE + "/api/v1/enhance", files={"file": ("m.jpg", f, "image/jpeg")}, data={"mode": "ultra"})
check("tolak mode ultra", r.status_code == 400, r.status_code)

# valid: job selesai + hasil 2x
with open(f"{SAMPLES}/low_00.jpg", "rb") as f:
    r = httpx.post(BASE + "/api/v1/enhance", files={"file": ("l.jpg", f, "image/jpeg")},
                   data={"mode": "basic", "strength": "medium"})
check("enqueue 200", r.status_code == 200, r.status_code)
jid = r.json()["job_id"]
st = {}
for _ in range(60):
    st = httpx.get(f"{BASE}/api/v1/jobs/{jid}").json()
    if st["status"] in ("completed", "failed"):
        break
    time.sleep(2)
check("job completed", st.get("status") == "completed", st)
img = httpx.get(f"{BASE}/api/v1/result/{jid}")
check("result png 200", img.status_code == 200 and img.headers["content-type"] == "image/png", img.status_code)
d = httpx.delete(f"{BASE}/api/v1/result/{jid}").json()
check("delete", d.get("deleted") == ["original", "processed"], d)

print("GAGAL:" if fails else "SEMUA LOLOS", fails)
sys.exit(1 if fails else 0)
