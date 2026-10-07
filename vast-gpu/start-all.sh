#!/bin/bash
# Hybrid: FLUX :8001, GFPGAN :8002, router :8000 (foreground).
set -e
cd /opt/restore
nohup python3 -m uvicorn server:app --host 127.0.0.1 --port 8001 > /tmp/flux.log 2>&1 &
cd /opt/gfpgan
nohup /opt/venvs/gfpgan/bin/python -m uvicorn gfpgan_server:app --host 127.0.0.1 --port 8002 > /tmp/gfpgan.log 2>&1 &
cd /opt/router
exec python3 -m uvicorn router:app --host 0.0.0.0 --port 8000
