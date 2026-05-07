from celery import Celery
from app.config import settings

celery_app = Celery(
    "repoarkeolog",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.analyze_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    worker_prefetch_multiplier=1,
)
