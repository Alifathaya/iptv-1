#!/bin/bash
# Setup Foto Jelas GPU server di Vast.ai (image pytorch runtime).
# Dipanggil via onstart. Log: /tmp/setup.log
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq curl libgl1 libglib2.0-0 > /dev/null 2>&1 || true
python3 -m pip install -q --upgrade pip
python3 -m pip install -q fastapi "uvicorn[standard]" python-multipart opencv-python-headless
python3 -m pip install -q basicsr facexlib gfpgan realesrgan
mkdir -p /opt/restore/weights
BRANCH="${FJ_BRANCH:-vast/gpu-restore}"
curl -sL "https://raw.githubusercontent.com/Alifathaya/iptv-1/${BRANCH}/vast-gpu/server.py" -o /opt/restore/server.py
# panaskan: download weights GFPGAN + RealESRGAN dulu
python3 -c "import sys; sys.path.insert(0,'/opt/restore'); from server import get_restorer; get_restorer(); print('WARMUP_OK')"
# jalan
cd /opt/restore
nohup python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 > /tmp/gpu-server.log 2>&1 &
echo "SETUP_DONE port 8000"
