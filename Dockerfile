# syntax=docker/dockerfile:1

# ---- frontend build stage ----
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- python runtime stage ----
FROM python:3.12-slim

LABEL org.opencontainers.image.title="homelab-music-toolkit" \
      org.opencontainers.image.description="Navidrome + AudioMuse toolkit, including duplicate-music finding" \
      org.opencontainers.image.source="https://github.com/mikestecker/docker-homelab-music-toolkit" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp \
    PORT=8095 \
    MUSIC_DIR=/music \
    CONFIG_DIR=/config

WORKDIR /app

# fpcalc (Chromaprint) for the duplicate finder's acoustic fingerprints.
# Optional at runtime: fingerprinting is skipped when it's missing.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libchromaprint-tools \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
COPY config-defaults/ ./config-defaults/
COPY --from=frontend /frontend/dist/ ./frontend/dist/

# Default non-root user. Override with `user: "UID:GID"` in compose (or
# `--user` on docker run) to match the owner of your music library. /config
# is world-writable so any UID you pick can write its state there, and the
# app files are made world-readable regardless of the host's umask.
RUN chmod -R a+rX /app && mkdir -p /config /music && chmod 0777 /config
USER 1000:1000

EXPOSE 8095
VOLUME ["/config"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8095\")}/healthz',timeout=4)" || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT}\""]
