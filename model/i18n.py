from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class I18NResult:
    detected_language: str
    translation_applied: bool
    translated_text: Optional[str]
    error: Optional[str]


def detect_language(text: str) -> str:
    """
    Best-effort language detection.
    Returns ISO-ish codes like 'en', 'hi', etc. Returns 'unknown' on failure.
    """
    try:
        from langdetect import detect  # type: ignore

        lang = detect(text)
        if not isinstance(lang, str) or not lang:
            return "unknown"
        return lang
    except Exception:
        return "unknown"


def translate_to_english(text: str, source_lang: str) -> I18NResult:
    """
    Best-effort translation to English. Never raises.
    If translation fails, returns translation_applied=False and translated_text=None.
    """
    if not isinstance(text, str) or not text.strip():
        return I18NResult(
            detected_language=source_lang or "unknown",
            translation_applied=False,
            translated_text=None,
            error="empty_text",
        )

    if source_lang in ("en", "unknown", ""):
        return I18NResult(
            detected_language=source_lang or "unknown",
            translation_applied=False,
            translated_text=None,
            error=None,
        )

    try:
        from deep_translator import GoogleTranslator  # type: ignore

        translated = GoogleTranslator(source=source_lang, target="en").translate(text)
        if not isinstance(translated, str) or not translated.strip():
            return I18NResult(
                detected_language=source_lang,
                translation_applied=False,
                translated_text=None,
                error="translation_empty",
            )
        return I18NResult(
            detected_language=source_lang,
            translation_applied=True,
            translated_text=translated,
            error=None,
        )
    except Exception as e:
        return I18NResult(
            detected_language=source_lang,
            translation_applied=False,
            translated_text=None,
            error=f"translation_failed: {type(e).__name__}",
        )
