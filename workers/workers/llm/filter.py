"""Response sanitization before sending to Telegram."""

from __future__ import annotations

import re

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SYSTEM_LEAK = re.compile(
    r"(?i)(as an ai|as a language model|system prompt|ignore previous instructions)"
)


def filter_llm_response(text: str) -> str | None:
    """Return cleaned text or None if response must not be sent."""
    if not text or not text.strip():
        return None
    cleaned = _CONTROL_CHARS.sub("", text).strip()
    if not cleaned:
        return None
    if _SYSTEM_LEAK.search(cleaned):
        return None
    # Drop fenced "thinking" / tool dumps that sometimes leak
    if cleaned.startswith("```") and "error" in cleaned.lower():
        return None
    return cleaned
