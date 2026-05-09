"""Mining metadata içinden (dosya uzantıları → dil) algılanan dil listesi."""


def detected_language_tags(metadata: dict) -> list[str]:
    """Dosya sayısına göre çoktan aza sıralı dil kimlikleri (örn. python, typescript)."""
    langs = metadata.get("languages") or {}
    if not langs:
        return []
    return sorted(langs.keys(), key=lambda k: langs[k], reverse=True)
