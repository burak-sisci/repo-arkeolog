"""LLM API anahtarı ortam doğrulaması (.env)."""
from __future__ import annotations

from fastapi import HTTPException

from app.config import settings

LLM_KEYS_USER_MESSAGE = (
    "Cerebras veya Gemini API Anahtarı eksik/geçersiz. Lütfen .env dosyanızı kontrol edin."
)


def _stripped(value: str | None) -> str:
    return (value or "").strip()


def llm_api_keys_present() -> bool:
    return bool(_stripped(settings.gemini_api_key) and _stripped(settings.cerebras_api_key))


def require_llm_api_keys_http() -> None:
    """POST /api/analyze: boş anahtarlar için anlamlı HTTP yanıtı."""
    if not llm_api_keys_present():
        raise HTTPException(status_code=400, detail=LLM_KEYS_USER_MESSAGE)


def llm_keys_task_error_message() -> str | None:
    """Celery görevi: eksik anahtarda kullanıcıya gösterilecek metin."""
    if llm_api_keys_present():
        return None
    return LLM_KEYS_USER_MESSAGE
