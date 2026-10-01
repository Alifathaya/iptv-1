"""Deteksi wajah: YuNet bila OpenCV mendukung, otomatis fallback Haar.
Box dipakai crop-restore-blend; bukan restore seluruh gambar."""
import os

import cv2
import numpy as np

from .base import Stage, StageResult

YUNET = os.getenv("YUNET_MODEL",
                  "/tmp/prestore-p1/photorestore/models/weights/face_detection_yunet_2023mar.onnx")
HAAR = os.getenv("HAAR_MODEL",
                 "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml")
MIN_SCORE = float(os.getenv("FACE_MIN_SCORE", "0.6"))

_detector = None
_engine = None  # "yunet" atau "haar"


def get_detector():
    global _detector, _engine
    if _detector is not None:
        return _detector, _engine
    try:
        if os.path.exists(YUNET):
            d = cv2.FaceDetectorYN_create(YUNET, "", (320, 320), MIN_SCORE, 0.3, 50)
            d.detect(np.zeros((320, 320, 3), np.uint8))  # smoke test
            _detector, _engine = d, "yunet"
            return _detector, _engine
    except cv2.error:
        pass
    if not os.path.exists(HAAR):
        raise RuntimeError("tidak ada model deteksi wajah (YuNet gagal, Haar tidak ada)")
    _detector, _engine = cv2.CascadeClassifier(HAAR), "haar"
    return _detector, _engine


class FaceDetect(Stage):
    name = "face_detect"

    def run(self, image: np.ndarray, ctx: dict) -> StageResult:
        h, w = image.shape[:2]
        det, engine = get_detector()
        boxes = []
        if engine == "yunet":
            det.setInputSize((w, h))
            _, faces = det.detect(image)
            if faces is not None:
                for f in faces:
                    x, y, bw, bh = int(f[0]), int(f[1]), int(f[2]), int(f[3])
                    x, y = max(0, x), max(0, y)
                    boxes.append({"box": [x, y, min(w - x, bw), min(h - y, bh)],
                                  "score": round(float(f[14]), 3)})
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            for (x, y, bw, bh) in det.detectMultiScale(gray, 1.1, 4):
                # Haar tanpa skor: minNeighbors=4 sudah ketat -> 0.8 agar lolos
                # gate konservatif (backend klasik CPU memang ringan)
                boxes.append({"box": [int(x), int(y), int(bw), int(bh)], "score": 0.8})
        boxes = [b for b in boxes if b["box"][2] > 20 and b["box"][3] > 20]
        ctx["faces"] = boxes
        return StageResult(image, {"count": len(boxes), "engine": engine})
