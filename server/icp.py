"""Stage 01 — turn a free-text product description into a buyer profile (ICP).

Deterministic keyword extraction today; structured so an LLM pass can replace
`_extract_keywords` without touching the pipeline.
"""

from __future__ import annotations

import re

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "in",
    "is", "it", "its", "of", "on", "or", "our", "that", "the", "to", "we", "with",
    "your", "you", "our", "their", "this", "these", "those", "into", "over",
}

DEFAULT_TITLES = [
    "Head of Procurement",
    "Sourcing Director",
    "VP Procurement",
    "Purchasing Manager",
    "Supply Chain Director",
    "COO",
]


def _extract_keywords(text: str, limit: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text.lower())
    seen: dict[str, int] = {}
    for w in words:
        if w not in STOPWORDS:
            seen[w] = seen.get(w, 0) + 1
    ranked = sorted(seen, key=lambda w: (-seen[w], w))
    return ranked[:limit]


def build_icp(product: str, overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    keywords = _extract_keywords(product)
    return {
        "product": product.strip(),
        "keywords": keywords,
        "titles": overrides.get("target_titles") or DEFAULT_TITLES,
        "countries": overrides.get("target_countries") or [],
        "industries": overrides.get("target_industries") or [],
    }
