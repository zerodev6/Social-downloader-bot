FROM python:3.10-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    git \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create necessary folders
RUN mkdir -p cookies downloads

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download spotdl dependencies
RUN spotdl --download-ffmpeg || true

COPY . .

CMD ["python", "bot.py"]
