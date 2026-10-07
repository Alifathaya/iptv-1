# Foto Jelas GPU — Flux soft-restore. Tag :flux1
# Pipeline: light Telea repair → FLUX.1-schnell img2img (strength~0.42) → mild sharpen
# NO DDColor / CodeFormer / GFPGAN / basicsr
# Weights downloaded at first /v1/warmup or restore on Vast
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/restore/hf \
    HUGGINGFACE_HUB_CACHE=/opt/restore/hf/hub \
    TRANSFORMERS_CACHE=/opt/restore/hf/hub \
    FLUX_MODEL_ID=black-forest-labs/FLUX.1-schnell \
    DIFFUSERS_ATTN_BACKEND=sdpa

RUN apt-get update -qq \
 && apt-get install -y -qq python3 python3-pip git libgl1 libglib2.0-0 curl \
 && rm -rf /var/lib/apt/lists/*

# Pin stack: diffusers 0.40 + torch 2.4 breaks on flash_attn_3 schema (float|None).
# torch 2.5.1 + diffusers 0.32.2 is a known-good Flux img2img combo.
RUN python3 -m pip install -q --no-cache-dir "numpy<2" \
      torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121 \
 && python3 -m pip install -q --no-cache-dir "numpy<2" \
      fastapi "uvicorn[standard]" python-multipart opencv-python-headless pillow \
      "diffusers==0.32.2" "transformers==4.46.3" "accelerate==1.2.1" \
      sentencepiece protobuf huggingface_hub safetensors "bitsandbytes==0.45.0" \
 && python3 -c "import torch, torchvision, diffusers, transformers, bitsandbytes; \
  print('OK', torch.__version__, torchvision.__version__, diffusers.__version__, transformers.__version__); \
  from diffusers import FluxImg2ImgPipeline; print('FLUX_IMG2IMG_IMPORT_OK')"

RUN mkdir -p /opt/restore/hf /opt/restore/weights
COPY server.py /opt/restore/server.py
WORKDIR /opt/restore
EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
