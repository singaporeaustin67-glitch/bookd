"""Runtime configuration, loaded from environment with optional .env file."""

from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"

if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


DB_PATH = _get("BOOKD_DB", str(_ROOT / "data" / "bookd.db"))
MEETINGS_DIR = _ROOT / "data" / "meetings"

# Lead providers
APOLLO_API_KEY = _get("APOLLO_API_KEY")
HUNTER_API_KEY = _get("HUNTER_API_KEY")

# LLM composer (OpenAI-compatible)
OPENAI_API_KEY = _get("OPENAI_API_KEY")
OPENAI_BASE_URL = _get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = _get("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")

# SMTP sender
SMTP_HOST = _get("SMTP_HOST")
SMTP_PORT = int(_get("SMTP_PORT", "587"))
SMTP_USER = _get("SMTP_USER")
SMTP_PASS = _get("SMTP_PASS")
FROM_EMAIL = _get("FROM_EMAIL", SMTP_USER)
FROM_NAME = _get("FROM_NAME", "BOOKD Outreach")

# Sender identity used in email copy
SENDER_COMPANY = _get("SENDER_COMPANY", "Our team")
SENDER_CALENDAR_URL = _get("SENDER_CALENDAR_URL", "")

# Safety caps
MAX_LEADS_PER_RUN = int(_get("MAX_LEADS_PER_RUN", "25"))
SEND_DELAY_SECONDS = float(_get("SEND_DELAY_SECONDS", "0"))


def capabilities() -> dict:
    """Honest report of which subsystems are live vs. inert."""
    return {
        "lead_providers": {
            "csv_import": True,
            "apollo": bool(APOLLO_API_KEY),
            "hunter": bool(HUNTER_API_KEY),
        },
        "composer": "llm" if (OPENAI_API_KEY or ANTHROPIC_API_KEY) else "template",
        "sender": "smtp" if (SMTP_HOST and SMTP_USER and SMTP_PASS) else "outbox_only",
        "llm_configured": bool(OPENAI_API_KEY or ANTHROPIC_API_KEY),
        "smtp_configured": bool(SMTP_HOST and SMTP_USER and SMTP_PASS),
    }
