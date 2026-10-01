"""Benchmark: 30 foto (low/med/high) -> waktu, memori RSS, resolusi out, gagal."""
import glob
import os
import sys
import time

import httpx
import psutil

BASE = os.getenv("API_BASE", "http://127.0.0.1:8101")
SAMPLES = os.path.join(os.path.dirname(__file__), "samples")

files = sorted(glob.glob(SAMPLES + "/*.jpg"))
assert len(files) == 30, f"butuh 30 sampel, ada {len(files)} (jalankan make_samples.py)"
proc = psutil.Process()
rss0 = proc.memory_info().rss // 1024 // 1024
rows = []
for fp in files:
    t0 = time.time()
    with open(fp, "rb") as f:
        jid = httpx.post(BASE + "/api/v1/enhance", files={"file": ("x.jpg", f, "image/jpeg")},
                         timeout=60).json()["job_id"]
    st = {}
    for _ in range(90):
        st = httpx.get(f"{BASE}/api/v1/jobs/{jid}", timeout=30).json()
        if st["status"] in ("completed", "failed"):
            break
        time.sleep(2)
    dt = time.time() - t0
    ok = st.get("status") == "completed"
    out = ""
    if ok:
        r = httpx.get(f"{BASE}/api/v1/result/{jid}", timeout=60)
        out = f"{len(r.content)//1024}KB"
        httpx.delete(f"{BASE}/api/v1/result/{jid}")
    rows.append((os.path.basename(fp), round(dt, 1), ok, out))
    print(os.path.basename(fp), round(dt, 1), "s", "OK" if ok else "GAGAL " + str(st))

rss1 = proc.memory_info().rss // 1024 // 1024
okn = sum(1 for r in rows if r[2])
avg = sum(r[1] for r in rows) / len(rows)
print(f"\nOK {okn}/30, rata-rata {avg:.1f}s/foto, RSS {rss0}->{rss1}MB")
