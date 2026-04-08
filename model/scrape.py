from __future__ import annotations

from typing import Optional

import requests
from bs4 import BeautifulSoup


def fetch_article_text(url: str, timeout_s: int = 12, max_chars: int = 8000) -> Optional[str]:
    """
    Scrape article text from <p> tags.
    Returns None if scraping fails or yields empty text.
    """
    if not isinstance(url, str) or not url.strip():
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; FakeNewsDetector/1.0; +https://example.com/bot)",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout_s)
        resp.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    ps = soup.find_all("p")
    parts = []
    for p in ps:
        t = p.get_text(" ", strip=True)
        if t:
            parts.append(t)

    text = "\n".join(parts).strip()
    if not text:
        return None
    if len(text) > max_chars:
        text = text[:max_chars]
    return text

