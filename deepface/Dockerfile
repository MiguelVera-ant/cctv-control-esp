FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema para OpenCV y compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-descargar el modelo Facenet512
RUN python -c "from deepface import DeepFace; DeepFace.build_model('Facenet512')"

COPY deepface_api.py .

EXPOSE 5001
CMD ["python", "deepface_api.py"]
