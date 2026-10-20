# Stage 1: Build stage
FROM python:3.11-bookworm AS builder

ENV PYTHONUNBUFFERED=1
WORKDIR /blt

# Install system dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 libmemcached-dev libz-dev \
    dos2unix \
    # OpenCV dependencies
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    libgtk-3-0 libavcodec-dev libavformat-dev libswscale-dev \
    libgstreamer-plugins-base1.0-dev libgstreamer1.0-dev \
    libpng-dev libjpeg-dev libopenexr-dev libtiff-dev libwebp-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Chromium (works on all architectures)
# Retry logic with --fix-missing for transient network errors
RUN apt-get update \
    && apt-get install -y --fix-missing chromium \
    || (apt-get update && apt-get install -y --fix-missing chromium) \
    && ln -sf /usr/bin/chromium /usr/local/bin/google-chrome \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies with uv into /opt/venv. The venv lives outside /blt so
# docker-compose's `.:/blt` bind mount does not hide it.
COPY --from=ghcr.io/astral-sh/uv:0.13.3 /uv /uvx /bin/
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON=/usr/local/bin/python3.11 \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
# INSTALL_DEV=true adds the dev group (debug toolbar, livereload) for DEBUG=True setups;
# docker-compose.yml sets it for local development.
ARG INSTALL_DEV=false
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$INSTALL_DEV" = "true" ]; then uv sync --frozen; else uv sync --frozen --no-dev; fi

# Stage 2: Runtime stage
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1
WORKDIR /blt

# Copy the virtualenv from the builder stage and put it first on PATH
COPY --from=builder /opt/venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Install runtime system dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 dos2unix \
    libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 \
    libgtk-3-0 libavcodec59 libavformat59 libswscale6 \
    libgstreamer-plugins-base1.0-0 libgstreamer1.0-0 \
    libpng16-16 libjpeg62-turbo libopenexr-3-1-30 libtiff6 libwebp7 && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /blt

# Convert line endings and set permissions
RUN dos2unix Dockerfile docker-compose.yml scripts/entrypoint.sh ./blt/settings.py
# Check if .env exists and run dos2unix on it, otherwise skip
RUN if [ -f /blt/.env ]; then dos2unix /blt/.env; fi
RUN chmod +x /blt/scripts/entrypoint.sh

ENTRYPOINT ["/blt/scripts/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
