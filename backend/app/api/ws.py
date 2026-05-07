import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
from app.config import settings

router = APIRouter()

# active connections: analysis_id -> list of WebSocket
_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/progress/{analysis_id}")
async def ws_progress(websocket: WebSocket, analysis_id: str):
    await websocket.accept()
    _connections.setdefault(analysis_id, []).append(websocket)
    try:
        # Subscribe to Redis pub/sub channel for this analysis
        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"progress:{analysis_id}")

        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"].decode())
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        conns = _connections.get(analysis_id, [])
        if websocket in conns:
            conns.remove(websocket)
        await websocket.close()
