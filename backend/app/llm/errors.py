"""LLM hatalarını kullanıcıya güvenli, Türkçe mesajlara çevirir."""
from __future__ import annotations


def user_message_for_exception(exc: BaseException, *, provider: str) -> str:
    """HTTP durumları ve tipik API gövdelerinden okunabilir mesaj üret."""
    msg = str(exc).lower()

    if provider == "gemini":
        if "gemini_api_key_missing" in msg:
            return (
                "Gemini API anahtarı eksik. Sunucu `.env` dosyasına GEMINI_API_KEY ekleyin (Google AI Studio)."
            )
        if any(x in msg for x in ("api key", "api_key", "invalid api", "permission denied", "blocked")):
            return (
                "Gemini API anahtarı eksik veya geçersiz. Sunucu `.env` içindeki GEMINI_API_KEY değerini "
                "kontrol edin (Google AI Studio anahtarı)."
            )
        if "404" in msg or "not found" in msg or ("model" in msg and "not found" in msg):
            return (
                "Gemini model veya embedding uç noktası bulunamadı (404). Model adı veya API erişiminizi "
                "kontrol edin; gömme (embedding) için kota veya bölge kısıtı olabilir."
            )
        if "429" in msg or "quota" in msg or "resourceexhausted" in msg.replace(" ", ""):
            return (
                "Gemini kota veya hız sınırına takıldı (429). Bir süre sonra tekrar deneyin veya "
                "Google AI Studio kotanızı kontrol edin."
            )

    if provider == "cerebras":
        if "cerebras_api_key_missing" in msg:
            return (
                "Cerebras API anahtarı eksik. `.env` içindeki CEREBRAS_API_KEY değerini ekleyin."
            )
        if any(x in msg for x in ("401", "403", "unauthorized", "invalid api key", "invalid_api_key")) or (
            "api key" in msg and "invalid" in msg
        ):
            return (
                "Cerebras API anahtarı geçersiz veya reddedildi. `.env` içindeki CEREBRAS_API_KEY değerini doğrulayın."
            )
        if "404" in msg or "not found" in msg:
            return (
                "Cerebras API uç noktası veya model bulunamadı (404). SDK/model adı ve hesap erişimini kontrol edin."
            )
        if "429" in msg or "rate" in msg or "throttl" in msg:
            return (
                "Cerebras hız sınırına takıldı (429). Birkaç dakika sonra tekrar deneyin veya plan kotanızı kontrol edin."
            )

    if any(x in msg for x in ("503", "502", "504", "unavailable", "overloaded", "timeout", "timed out")):
        return f"{provider.capitalize()} geçici olarak kullanılamıyor. Lütfen kısa süre sonra tekrar deneyin."

    return f"{provider.capitalize()} çağrısı başarısız: {type(exc).__name__}"
