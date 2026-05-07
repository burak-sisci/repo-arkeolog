#!/bin/sh
set -e

# 1) DB migration (idempotent)
echo "[start-web] alembic upgrade head"
alembic upgrade head || echo "[start-web] alembic atlandı (DB hazır mı?)"

# 2) Uvicorn — Railway $PORT'u otomatik enjekte eder
PORT="${PORT:-8000}"
echo "[start-web] uvicorn :$PORT"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --proxy-headers --forwarded-allow-ips '*'
