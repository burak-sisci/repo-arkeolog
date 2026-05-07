"""WebSocket ilerleme bildirimleri — Redis pub/sub üzerinden."""
import json
import logging
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)


async def push_progress(analysis_id: str, stage: str, message: str, progress_pct: int):
    payload = json.dumps({"stage": stage, "message": message, "progress_pct": progress_pct})
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.publish(f"progress:{analysis_id}", payload)
        await r.aclose()
    except Exception as e:
        logger.warning(f"push_progress failed: {e}")
