# Backend (FastAPI + Celery worker) — Railway servis imajı
# Aynı imaj iki servis tarafından kullanılır:
#   - "backend" web servisi   : start command -> ./start-web.sh
#   - "worker"  Celery worker : start command -> ./start-worker.sh

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Sistem bağımlılıkları (psycopg2 build, git clone)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        libpq-dev \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bağımlılıkları önce kopyala — layer cache verimi
COPY pyproject.toml /app/
RUN pip install --upgrade pip && pip install -e .

# Kaynak kod
COPY . /app/

# Start script'lerini executable yap
RUN chmod +x /app/start-web.sh /app/start-worker.sh

EXPOSE 8000

# Default: web. Railway worker servisinde override edilir.
CMD ["/app/start-web.sh"]
