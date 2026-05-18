# Backend Dockerfile for RealTime-FaceDetec
# Build: docker build -f docker/backend.Dockerfile -t realtime-facedetec-backend .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    DEEPFACE_HOME=/root/.deepface

WORKDIR /app

# System libraries needed by FastAPI, psycopg2, Pillow/OpenCV/DeepFace/TensorFlow.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install -r /app/requirements.txt

# Copy backend source code.
COPY src/backend /app/src/backend

# Persistent folders. docker-compose mounts volumes here.
RUN mkdir -p /app/data /app/media /root/.deepface

WORKDIR /app/src/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
