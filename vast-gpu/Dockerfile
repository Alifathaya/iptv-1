# Foto Jelas GPU — image jadi (program + model dibungkus, nyala ±3 menit)
# torch 2.1.x: basicsr butuh torchvision.transforms.functional_tensor
# (modul itu dibuang di torchvision 0.17+, jadi jangan pakai base 2.2/2.4)
FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update -qq \
 && apt-get install -y -qq libgl1 libglib2.0-0 curl \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install -q --upgrade pip \
 && python3 -m pip install -q --no-cache-dir "numpy<2" \
      fastapi "uvicorn[standard]" python-multipart opencv-python-headless \
      basicsr facexlib gfpgan realesrgan \
 && python3 -c "import numpy, torch; assert numpy.__version__.startswith('1.'), numpy.__version__; print('NUMPY_TORCH_OK', numpy.__version__)"

# bakar weights ke dalam image (tidak download tiap nyala)
RUN mkdir -p /opt/restore/weights && python3 -c \
 "from basicsr.utils.download_util import load_file_from_url as d; \
  d('https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth','/opt/restore/weights'); \
  d('https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth','/opt/restore/weights'); \
  print('WEIGHTS_OK')"

COPY server.py /opt/restore/server.py
WORKDIR /opt/restore
EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
