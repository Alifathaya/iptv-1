"""Test API: upload valid/invalid + alur job sampai completed."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import httpx

BASE = os.getenv("API_BASE", "http://127.0.0.1:8101")
SAMPLES = os.path.join(os.path.dirname(__file__), "samples")

reg = httpx.post(BASE + "/auth/register", timeout=30).json()
H = {"X-Api-Key": reg["api_key"]}
# jadikan premium agar kuota tak mengganggu test alur
httpx.post(f"{BASE}/admin/premium/{reg['user_id']}",
           headers={"X-Admin-Token": os.getenv("ADMIN_TOKEN", "admin-dev-ganti-di-prod")}, timeout=30)

fails = []


def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name, info)
    if not cond:
        fails.append(name)


# invalid: bukan gambar
r = httpx.post(BASE + "/api/v1/enhance", files={"file": ("x.txt", b"halo", "text/plain")}, headers=H)
check("tolak text/plain", r.status_code == 415, r.status_code)
# invalid: bytes rusak
r = httpx.post(BASE + "/api/v1/enhance", files={"file": ("x.jpg", b"\xff\xd8corrupt", "image/jpeg")}, headers=H)
check("tolak corrupt", r.status_code == 400, r.status_code)
# invalid: terlalu kecil (10x10)
from PIL import Image
import io

buf = io.BytesIO()
Image.new("RGB", (10, 10)).save(buf, "JPEG")
r = httpx.post(BASE + "/api/v1/enhance", files={"file": ("k.jpg", buf.getvalue(), "image/jpeg")}, headers=H)
check("tolak terlalu kecil", r.status_code == 400, r.status_code)
# invalid: mode tidak dikenal
with open(f"{SAMPLES}/med_00.jpg", "rb") as f:
    r = httpx.post(BASE + "/api/v1/enhance", files={"file": ("m.jpg", f, "image/jpeg")}, data={"mode": "mega"}, headers=H)
check("tolak mode mega", r.status_code == 400, r.status_code)

# valid: job selesai + hasil 2x
with open(f"{SAMPLES}/low_00.jpg", "rb") as f:
    r = httpx.post(BASE + "/api/v1/enhance", files={"file": ("l.jpg", f, "image/jpeg")},
                   data={"mode": "basic", "strength": "medium"}, headers=H)
check("enqueue 200", r.status_code == 200, r.status_code)
jid = r.json()["job_id"]
st = {}
for _ in range(60):
    st = httpx.get(f"{BASE}/api/v1/jobs/{jid}", headers=H).json()
    if st["status"] in ("completed", "failed"):
        break
    time.sleep(2)
check("job completed", st.get("status") == "completed", st)
img = httpx.get(f"{BASE}/api/v1/result/{jid}", headers=H)
check("result png 200", img.status_code == 200 and img.headers["content-type"] == "image/png", img.status_code)
d = httpx.delete(f"{BASE}/api/v1/result/{jid}", headers=H).json()
check("delete", d.get("deleted") == ["original", "processed"], d)

print("GAGAL:" if fails else "SEMUA LOLOS", fails)
sys.exit(1 if fails else 0)
