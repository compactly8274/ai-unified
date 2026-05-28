# syntax=docker/dockerfile:1.4   # enables BuildKit features

FROM python:3.11-slim

# -----------------------------------------------------------------
# Install system‑level build tools (required for any C extensions)
# -----------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libc-dev \
        python3-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------
# Application work directory
# -----------------------------------------------------------------
WORKDIR /app

# -----------------------------------------------------------------
# Copy the whole project (adjust if you want a slimmer context)
# -----------------------------------------------------------------
COPY . .

# -----------------------------------------------------------------
# Install the package (normal install – containers are immutable)
# -----------------------------------------------------------------
RUN pip install --no-cache-dir .

# -----------------------------------------------------------------
# Default command – adjust if your library provides a different entrypoint
# -----------------------------------------------------------------
CMD ["python", "-m", "ai_unified"]
