#!/bin/sh
set -e

echo "[start-worker] celery worker başlıyor"
exec celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
