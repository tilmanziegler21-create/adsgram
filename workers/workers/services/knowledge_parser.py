"""Extract and clean text from URLs and files (DoD: ≤ 60s)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

try:
    import trafilatura
except ImportError:
    trafilatura = None  # type: ignore[assignment]

_MAX_CHARS = 50000
_WHITESPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    cleaned = _WHITESPACE.sub(" ", text).strip()
    if len(cleaned) > _MAX_CHARS:
        return cleaned[:_MAX_CHARS]
    return cleaned


def _extract_html(html: str) -> str:
    if trafilatura is not None:
        extracted = trafilatura.extract(html, include_comments=False, include_tables=True)
        if extracted and extracted.strip():
            return _normalize(extracted)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    return _normalize(soup.get_text(separator=" ", strip=True))


def extract_from_url(url: str, timeout: float = 55.0) -> dict:
    """Fetch URL and return structured knowledge_base payload."""
    started = datetime.now(timezone.utc)
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "TelegramFlow/1.0 (+https://teleflow.local)"},
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        html = response.text

    text = _extract_html(html)
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()

    return {
        "source_type": "url",
        "source_url": url,
        "content_type": content_type,
        "text": text,
        "char_count": len(text),
        "parsed_at": started.isoformat(),
        "duration_sec": round(elapsed, 2),
        "parser": "trafilatura+bs4" if trafilatura else "bs4",
    }


def extract_from_file(file_path: str) -> dict:
    """Extract text from TXT or PDF file."""
    started = datetime.now(timezone.utc)
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()
    text = ""
    if suffix == ".txt":
        text = _normalize(path.read_text(encoding="utf-8", errors="ignore"))
    elif suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        text = _normalize("\n".join(parts))
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    return {
        "source_type": "file",
        "source_path": str(path),
        "text": text,
        "char_count": len(text),
        "parsed_at": started.isoformat(),
        "duration_sec": round(elapsed, 2),
        "parser": suffix,
    }
