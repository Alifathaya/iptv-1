"""Test split GPU worker: remote OK via stub, fallback lokal bila GPU mati."""
import base64
import json
import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

os.environ["GPU_WORKER_URL"] = "http://127.0.0.1:8199"
os.environ["GPU_TIMEOUT"] = "30"

import cv2
import numpy as np
from http.server import BaseHTTPRequestHandler, HTTPServer

import pipeline.remote as remote

fails = []


def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name, info)
    if not cond:
        fails.append(name)


class Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n))
        raw = base64.b64decode(body["image"].split(",", 1)[1])
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if body["stage"] == "upscale":
            img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
        ok, buf = cv2.imencode(".png", img)
        out = {"image_b64": "data:image/png;base64," + base64.b64encode(bytes(buf)).decode()}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 8199), Stub)
threading.Thread(target=srv.serve_forever, daemon=True).start()

img = np.full((64, 64, 3), 128, np.uint8)
r1 = remote.run_stage("upscale", img, {"scale": 2})
check("remote upscale 2x", r1.shape[:2] == (128, 128), r1.shape)
r2 = remote.run_stage("deblur", img, {"strength": "medium"})
check("remote deblur ok", r2.shape == img.shape, r2.shape)

# fallback: URL mati -> GpuUnavailable (pipeline pakai ini untuk fallback lokal)
remote.GPU_URL = "http://127.0.0.1:9"
try:
    remote.run_stage("upscale", img, {"scale": 2})
    check("fallback terpicu", False, "tidak raise")
except remote.GpuUnavailable as e:
    check("fallback terpicu", True, str(e)[:60])

# pipeline penuh tetap jalan tanpa GPU (fallback lokal)
from pipeline.deblur import DeblurProcessor
from pipeline.face_restore import FaceRestore
from pipeline.upscale import Upscale

ctx = {"strength": "light", "fidelity": 0.8, "faces": []}
d = DeblurProcessor().run(img, ctx).notes
check("deblur fallback lokal", d["backend"] == "rl-fft", d)
u = Upscale().run(img, {**ctx}).notes
check("upscale fallback lokal", u["backend"] == "lanczos", u)
fr = FaceRestore().run(img, ctx).notes
check("face fallback lokal", fr["backend"] == "classical", fr)

srv.shutdown()
print("GAGAL:" if fails else "SEMUA LOLOS", fails)
sys.exit(1 if fails else 0)
