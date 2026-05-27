FROM python:3.11-slim

# Sistem güncellemeleri ve ffmpeg kurulumu
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# yt-dlp kurulumu
RUN pip install yt-dlp

# Çalışma dizini
WORKDIR /app

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Sunucuyu çalıştır
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]