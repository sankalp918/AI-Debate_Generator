FROM pytorch/pytorch:1.13.1-cuda11.6-cudnn8-devel

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies needed for PyAV and other packages
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    unzip \
    pkg-config \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone SadTalker
RUN git clone https://github.com/OpenTalker/SadTalker.git
WORKDIR /app/SadTalker

# Install Python dependencies in correct order
RUN pip install --upgrade pip setuptools wheel

# Install PyTorch first
RUN pip install torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1

# Install problematic packages individually with verbose output
RUN pip install --verbose av==10.0.0

# Install safetensors first (this is crucial)
RUN pip install \
    safetensors==0.4.1 \
    kornia==0.6.12 \
    imageio==2.31.1 \
    imageio-ffmpeg==0.4.8 \
    basicsr==1.4.2 \
    realesrgan==0.3.0

# Install other requirements
RUN pip install \
numpy==1.23.4 \
face_alignment==1.3.5 \
imageio==2.19.3 \
imageio-ffmpeg==0.4.7 \
librosa==0.9.2 \
numba \
resampy==0.3.1 \
pydub==0.25.1 \
scipy==1.10.1 \
kornia==0.6.8 \
tqdm \
yacs==0.1.8 \
pyyaml  \
joblib==1.1.0 \
scikit-image==0.19.3 \
basicsr==1.4.2 \
facexlib==0.3.0 \
gradio \
gfpgan \
av \
safetensors

# Install Flask for web service
RUN pip install flask==2.3.3 requests==2.31.0

# Create checkpoints directory and download models
RUN mkdir -p checkpoints

# Download SadTalker models
WORKDIR /app/SadTalker/checkpoints
RUN wget -O mapping_00109-model.pth.tar \
    "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00109-model.pth.tar" \
    && wget -O mapping_00229-model.pth.tar \
    "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00229-model.pth.tar" \
    && wget -O SadTalker_V002_512.safetensors \
    "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_512.safetensors" \
    && wget -O SadTalker_V0.0.2_256.safetensors \
    "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_256.safetensors"

# Download face detection model
RUN mkdir -p ../gfpgan/weights && cd ../gfpgan/weights \
    && wget -O GFPGANv1.4.pth \
    "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth"

# Download face parsing model
RUN mkdir -p ../face_parsing && cd ../face_parsing \
    && wget -O 79999_iter.pth \
    "https://huggingface.co/GRAD04/Wav2LipGAN/resolve/main/79999_iter.pth"

WORKDIR /app
COPY . .

# Install our additional requirements (including safetensors again to be sure)
RUN pip install -r requirements.txt

EXPOSE 8003

CMD ["python", "sadtalker_service.py"]