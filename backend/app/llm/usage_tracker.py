"""LLM API kullanımını izler ve eşik aşılınca uyarı verir."""
from __future__ import annotations
import asyncio
import logging
import time
from collections import defaultdict
from app.config import settings

logger = logging.getLogger(__name__)


class UsageTracker:
    def __init__(self):
        self._counts: dict[str, list[float]] = defaultdict(list)  # service -> timestamps

    def record(self, service: str, tokens: int = 0):
        now = time.time()
        self._counts[service].append(now)
        # Prune old entries (> 60s)
        self._counts[service] = [t for t in self._counts[service] if now - t < 60]

        if self._exceeds_threshold(service):
            asyncio.create_task(self._alert(service))

    def _rpm(self, service: str) -> int:
        now = time.time()
        return sum(1 for t in self._counts[service] if now - t < 60)

    def _exceeds_threshold(self, service: str) -> bool:
        rpm = self._rpm(service)
        thresholds = {
            "gemini": settings.gemini_rpm_threshold,
            "groq": settings.groq_rpm_threshold,
        }
        return rpm >= thresholds.get(service, 99999)

    async def _alert(self, service: str):
        rpm = self._rpm(service)
        msg = f"[RepoArkeolog] {service.upper()} rate limit uyarısı: {rpm} RPM"
        logger.warning(msg)
        if settings.admin_webhook_url:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(settings.admin_webhook_url, json={"content": msg}, timeout=5)
            except Exception:
                pass

    def get_status(self) -> dict:
        def _level(service: str, threshold: int) -> str:
            rpm = self._rpm(service)
            if rpm >= threshold:
                return "red"
            if rpm >= threshold * 0.6:
                return "yellow"
            return "green"

        return {
            "gemini_status": _level("gemini", settings.gemini_rpm_threshold),
            "groq_status": _level("groq", settings.groq_rpm_threshold),
            "gemini_rpm_current": self._rpm("gemini"),
            "groq_rpm_current": self._rpm("groq"),
        }


usage_tracker = UsageTracker()
