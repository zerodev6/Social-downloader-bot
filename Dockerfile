FROM python:3.10-slim

# Set environment variables to prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (Essential for Telegram bots and Media processing)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    git \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create necessary folders for cookies and downloads
RUN mkdir -p cookies downloads

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download spotdl-specific ffmpeg binaries (Required for Spotify)
RUN spotdl --download-ffmpeg || true

# Copy all project files (including your youtube.txt)
COPY . .

# Ensure the cookie file has the correct permissions
RUN chmod 644 youtube.txt || true

# Start the bot
CMD ["python", "bot.py"]
