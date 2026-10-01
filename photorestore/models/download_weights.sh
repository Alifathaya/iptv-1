#!/bin/bash
# Download weights Phase 3 (dijalankan sekali di worker/GPU).
set -e
DIR="$(dirname "$0")/weights"
mkdir -p "$DIR"
YUNET="$DIR/face_detection_yunet_2023mar.onnx"
[ -f "$YUNET" ] || curl -sL -o "$YUNET" https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
echo "YuNet OK"
# GFPGAN (otomatis bila tersedia, GPU): ~350MB
if [ "${WITH_GFPGAN:-0}" = "1" ]; then
  curl -sL -o "$DIR/GFPGANv1.4.pth" https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth
  echo "GFPGAN OK (lisensi Apache-2.0, aman komersial)"
fi
