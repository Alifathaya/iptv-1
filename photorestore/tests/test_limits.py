"""Test Phase 7: register -> kuota -> 429 -> premium -> lolos + usage tercatat."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import httpx

BASE = os.getenv("API_BASE", "http://127.0.0.1:8101")
SAMPLES = os.path.join(os.path.dirname(__file__), "samples")
ADMIN = os.getenv("ADMIN_TOKEN", "admin-dev-ganti-di-prod")

fails = []


def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name, info)
    if not cond:
        fails.append(name)


r = httpx.post(BASE + "/auth/register", timeout=30)
check("register 200 + api_key", r.status_code == 200 and r.json().get("api_key"), r.status_code)
uid, key = r.json()["user_id"], r.json()["api_key"]
H = {"X-Api-Key": key}

# tanpa key -> 401
with open(f"{SAMPLES}/med_00.jpg", "rb") as f:
    r = httpx.post(BASE + "/api/v1/enhance", files={"file": ("m.jpg", f, "image/jpeg")}, timeout=30)
check("tanpa key 401", r.status_code == 401, r.status_code)

# key salah -> 401
with open(f"{SAMPLES}/med_00.jpg", "rb") as f:
    r = httpx.post(BASE + "/api/v1/enhance", files={"file": ("m.jpg", f, "image/jpeg")},
                   headers={"X-Api-Key": "salah"}, timeout=30)
check("key salah 401", r.status_code == 401, r.status_code)


def enhance():
    with open(f"{SAMPLES}/med_00.jpg", "rb") as f:
        return httpx.post(BASE + "/api/v1/enhance", files={"file": ("m.jpg", f, "image/jpeg")},
                          headers=H, timeout=60)


import time

# habiskan kuota gratis (default 5)
codes = [enhance().status_code for _ in range(5)]
check("5x dalam kuota 200", all(c == 200 for c in codes), codes)
r = enhance()
check("kelebihan 429", r.status_code == 429, r.status_code)

# usage tercatat (tunggu worker)
for _ in range(60):
    q = httpx.get(BASE + "/api/v1/me", headers=H, timeout=30).json()["quota"]
    if q["used"] >= 5:
        break
    time.sleep(2)
check("usage tercatat 5", q["used"] == 5, q)

# upgrade premium -> lolos lagi
r = httpx.post(f"{BASE}/admin/premium/{uid}", headers={"X-Admin-Token": ADMIN}, timeout=30)
check("upgrade premium", r.status_code == 200, r.status_code)
check("premium lolos", enhance().status_code == 200, "")

print("GAGAL:" if fails else "SEMUA LOLOS", fails)
sys.exit(1 if fails else 0)
