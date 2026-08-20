# Stegstr Docker Image v2.1.1
# Build:  docker build -t stegstr:latest .
# Run:    docker run --rm -v $(pwd):/data stegstr:latest embed /data/cover.png "Hello" -o /data/stego.png

FROM python:3.12-slim

LABEL maintainer="stegstr@example.com"
LABEL version="2.1.1"
LABEL description="Robust steganographic client for social media"

WORKDIR /app

# Install system dependencies for Pillow, numpy, scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY stegstr/ ./stegstr/

# Install Python package
RUN pip install --no-cache-dir -e ".[full]"

# Create non-root user for security
RUN useradd -m -u 1000 stegstr
USER stegstr

# Default entrypoint
ENTRYPOINT ["python", "-m", "stegstr.cli"]
CMD ["--help"]
