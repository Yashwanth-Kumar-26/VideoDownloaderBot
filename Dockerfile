FROM python:3.11-slim

# Install system dependencies (FFmpeg is required)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set Env
ENV PYTHONUNBUFFERED=1

# Run the entrypoint script
CMD ["python", "entrypoint.py"]
