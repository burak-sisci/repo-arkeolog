"""Groq Llama 3.3 70B istemcisi — Tarihçi ajan ve fallback."""
from __future__ import annotations
import json
import logging
import re
from app.config import settings
from app.llm.usage_tracker import usage_tracker

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from groq import Groq
            self._client = Groq(api_key=settings.groq_api_key)
        return self._client

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        import asyncio
        usage_tracker.record("groq")
        client = self._get_client()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=4096,
            ),
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


groq_client = GroqClient()
