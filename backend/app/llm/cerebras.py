"""Cerebras Llama 3.3 70B istemcisi — yüksek throughput (~2000 tok/s)."""
from __future__ import annotations
import asyncio
import json
import logging
import re

from app.config import settings
from app.llm.usage_tracker import usage_tracker

logger = logging.getLogger(__name__)

MODEL = "qwen-3-235b-a22b-instruct-2507"


async def _call_with_retry(fn, *, max_attempts: int = 5, base_delay: float = 4.0):
    attempt = 0
    while True:
        try:
            return await asyncio.get_event_loop().run_in_executor(None, fn)
        except Exception as e:
            msg = str(e)
            transient = (
                "429" in msg
                or "503" in msg
                or "500" in msg
                or "502" in msg
                or "504" in msg
                or "timeout" in msg.lower()
                or "timed out" in msg.lower()
                or "rate" in msg.lower()
                or "overloaded" in msg.lower()
                or "APITimeoutError" in type(e).__name__
                or "APIConnectionError" in type(e).__name__
            )
            attempt += 1
            if not transient or attempt >= max_attempts:
                raise
            delay = base_delay * attempt
            logger.warning(f"Cerebras transient ({msg[:80]}), retry {attempt}/{max_attempts} after {delay:.0f}s")
            await asyncio.sleep(delay)


class CerebrasClient:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from cerebras.cloud.sdk import Cerebras
            # Büyük repo'larda generation 60s'i geçebilir; 240s timeout + 2 retry
            self._client = Cerebras(api_key=settings.cerebras_api_key, timeout=240.0, max_retries=2)
        return self._client

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        usage_tracker.record("cerebras")
        client = self._get_client()
        response = await _call_with_retry(
            lambda: client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=4096,
            )
        )
        return response.choices[0].message.content

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        text = await self.generate(system_prompt, user_prompt)
        return _parse_json(text)


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"JSON parse failed: {text[:200]}")


cerebras_client = CerebrasClient()
