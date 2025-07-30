FROM python:3.11-slim

WORKDIR /app
COPY . .

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        build-essential \
        libasound2-dev \
        portaudio19-dev \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 5002
CMD ["python", "app.py"]
