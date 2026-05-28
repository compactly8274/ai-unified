FROM python:3.11-slim

# Install system build dependencies required for compiling any C extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libc-dev \
        python3-dev \
        libffi-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Ensure pip is up‑to‑date and install the package without using cache
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir .

CMD ["python", "-m", "ai_unified"]
