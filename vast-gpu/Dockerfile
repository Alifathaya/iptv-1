# Foto Jelas GPU slim (~5GB): cuda-runtime + pip torch (bukan image conda gemuk).
# torch 2.1.x: basicsr butuh torchvision.transforms.functional_tensor.
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update -qq \
 && apt-get install -y -qq python3 python3-pip git libgl1 libglib2.0-0 curl \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install -q --no-cache-dir "numpy<2" \
      torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu121 \
 && python3 -m pip install -q --no-cache-dir "numpy<2" \
      fastapi "uvicorn[standard]" python-multipart opencv-python-headless \
      "basicsr==1.4.2" "facexlib==0.3.0" "gfpgan==1.0.4" "realesrgan==0.3.0" \
      timm huggingface_hub tqdm \
 && python3 -m pip install -q --no-cache-dir "numpy<2" \
      git+https://github.com/piddnad/DDColor.git \
 && python3 -c "import numpy, torch; assert numpy.__version__.startswith('1.'); print('TORCH_OK', torch.__version__)"

# bakar weights ke dalam image (tidak download tiap nyala)
RUN mkdir -p /opt/restore/weights && python3 -c \
 "from torch.hub import download_url_to_file as d; \
  d('https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth','/opt/restore/weights/GFPGANv1.4.pth'); \
  d('https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth','/opt/restore/weights/RealESRGAN_x4plus.pth'); \
  print('WEIGHTS_OK')" \
 && python3 -c \
 "from huggingface_hub import snapshot_download; import glob, shutil, os; \
  d = snapshot_download('piddnad/ddcolor_modelscope'); \
  pts = glob.glob(d + '/**/*.pt', recursive=True) + glob.glob(d + '/**/*.pth', recursive=True) + glob.glob(d + '/**/*.bin', recursive=True); \
  assert pts, 'ddcolor weights tidak ketemu: ' + str(os.listdir(d)); \
  shutil.copy(pts[0], '/opt/restore/weights/ddcolor_modelscope.pt'); \
  print('DDCOLOR_OK', pts[0])" \
 && python3 -c \
 "from facexlib.detection import init_detection_model; \
  init_detection_model('retinaface_resnet50', half=False, device='cpu'); \
  print('FACEDET_OK')"

COPY server.py /opt/restore/server.py
WORKDIR /opt/restore
EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
