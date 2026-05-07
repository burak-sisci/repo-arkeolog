"""Gemini 2.5 Flash ve text-embedding-004 istemcisi."""
from __future__ import annotations
import asyncio
import json
import logging
import re
from app.config import settings
from app.llm.usage_tracker import usage_tracker

logger = logging.getLogger(__name__)


_gemini_lock = asyncio.Lock()
_last_call_ts: float = 0.0
MIN_INTERVAL = 13.0  # ~4.6 RPM, free tier 5 RPM altında kalır


async def _throttle():
    global _last_call_ts
    async with _gemini_lock:
        now = asyncio.get_event_loop().time()
        wait = MIN_INTERVAL - (now - _last_call_ts)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call_ts = asyncio.get_event_loop().time()


async def _call_with_retry(fn, *, max_attempts: int = 8, base_delay: float = 10.0, throttle: bool = True):
    """429/503 hatalarında backoff ile yeniden dener."""
    attempt = 0
    while True:
        if throttle:
            await _throttle()
        try:
            return await asyncio.get_event_loop().run_in_executor(None, fn)
        except Exception as e:
            msg = str(e)
            transient = (
                "429" in msg
                or "503" in msg
                or "ResourceExhausted" in msg
                or "Unavailable" in msg
                or "quota" in msg.lower()
                or "overloaded" in msg.lower()
            )
            attempt += 1
            if not transient or attempt >= max_attempts:
                raise
            delay = base_delay * attempt
            m = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", msg)
            if m:
                delay = max(delay, int(m.group(1)) + 2)
            logger.warning(f"Gemini transient ({msg[:80]}), retry {attempt}/{max_attempts} after {delay:.0f}s")
            await asyncio.sleep(delay)


class GeminiClient:
    def __init__(self):
        self._model = None
        self._embed_model = None

    def _get_model(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            self._model = genai.GenerativeModel("gemini-2.5-flash")
        return self._model

    def _get_embed_model(self):
        if self._embed_model is None:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
        return "models/gemini-embedding-001"

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Gemini ile metin üret. JSON beklenen yerlerde JSON döner."""
        import google.generativeai as genai

        usage_tracker.record("gemini")
        model = self._get_model()

        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = await _call_with_retry(lambda: model.generate_content(full_prompt))
        return response.text

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        text = await self.generate(system_prompt, user_prompt)
        return _parse_json(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import google.generativeai as genai

        usage_tracker.record("gemini")
        results = []
        for text in texts:
            result = await _call_with_retry(
                lambda t=text: genai.embed_content(
                    model=self._get_embed_model(),
                    content=t,
                    task_type="retrieval_document",
                    output_dimensionality=768,
                ),
                throttle=False,
            )
            results.append(result["embedding"])
        return results

    async def embed_query(self, text: str) -> list[float]:
        import google.generativeai as genai

        usage_tracker.record("gemini")
        result = await _call_with_retry(
            lambda: genai.embed_content(
                model=self._get_embed_model(),
                content=text,
                task_type="retrieval_query",
                output_dimensionality=768,
            ),
            throttle=False,
        )
        return result["embedding"]

    async def stream_generate(self, system_prompt: str, user_prompt: str):
        """Streaming generator — yields text chunks."""
        import google.generativeai as genai

        usage_tracker.record("gemini")
        model = self._get_model()
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(full_prompt, stream=True),
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM response, stripping markdown code fences."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find first { ... } block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"JSON parse failed: {text[:200]}")


gemini_client = GeminiClient()
