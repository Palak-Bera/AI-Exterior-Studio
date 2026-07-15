# AI Exterior Studio - Backend (FastAPI, CPU-only)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODEL_CACHE_DIR=storage/models

# OpenCV needs libgl/glib (used by classical rendering / image IO).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install matching CPU torch + torchvision (+cpu pins avoid CUDA from PyPI).
COPY requirements.txt constraints-cpu.txt ./
RUN pip install --upgrade pip \
    && pip install torch==2.5.1+cpu torchvision==0.20.1+cpu \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
    && grep -vE '^(torch|torchvision)([=<>!~]|$)' requirements.txt > /tmp/requirements-notorch.txt \
    && pip install -r /tmp/requirements-notorch.txt -c constraints-cpu.txt

COPY . .

# Entrypoint generates placeholder textures (if missing) then starts the server.
# Normalize potential CRLF line endings (Windows hosts) before making executable.
RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
