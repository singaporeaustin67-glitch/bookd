"""Stage 03 — write the email.

Two real paths:
  - LLM path, when OPENAI_API_KEY (OpenAI-compatible) or ANTHROPIC_API_KEY is set
  - Deterministic personalization engine otherwise (no fake "AI" claims — the
    config endpoint reports which one is active)
"""

from __future__ import annotations

import httpx

from . import config

SYSTEM_PROMPT = (
    "You write short, specific B2B cold emails. 90-130 words. One clear ask: a 20-minute call. "
    "Reference the recipient's role and company. No hype, no buzzwords, no emojis. "
    "Output JSON with keys: subject, body."
)


def _llm_compose(lead: dict, icp: dict) -> dict | None:
    prompt = (
        f"Product we sell: {icp['product']}\n"
        f"Recipient: {lead['first_name']} {lead['last_name']}, {lead['title']} at {lead['company']} "
        f"({lead['industry'] or 'industry unknown'}, {lead['country'] or 'location unknown'}).\n"
        f"Sender: {config.FROM_NAME} at {config.SENDER_COMPANY}.\n"
        "Write the email."
    )
    try:
        if config.OPENAI_API_KEY:
            resp = httpx.post(
                f"{config.OPENAI_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                json={
                    "model": config.OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.7,
                },
                timeout=60,
            )
            resp.raise_for_status()
            import json

            content = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            return {"subject": data["subject"], "body": data["body"]}
        if config.ANTHROPIC_API_KEY:
            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": config.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 600,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=60,
            )
            resp.raise_for_status()
            import json

            text = resp.json()["content"][0]["text"]
            data = json.loads(text)
            return {"subject": data["subject"], "body": data["body"]}
    except Exception:
        return None  # fall back to template path — never send a broken draft
    return None


def _template_compose(lead: dict, icp: dict) -> dict:
    first = lead["first_name"] or "there"
    company = lead["company"] or "your team"
    role = lead["title"] or "your role"
    product = icp["product"].rstrip(".")
    hook = f"As {role} at {company}, " if lead["title"] else ""
    cal = f"\n\nGrab any slot that suits you: {config.SENDER_CALENDAR_URL}" if config.SENDER_CALENDAR_URL else ""
    subject = f"{product.split(',')[0].strip()[:60]} — worth 20 minutes?"
    body = (
        f"Hi {first},\n\n"
        f"{hook}I imagine sourcing the right supplier for {product.lower()} is on your desk more often than you'd like.\n\n"
        f"We help companies like {company} with exactly that — {product}. "
        f"Rather than a pitch deck, I'd suggest a short call: you tell me what you're buying, "
        f"I'll tell you plainly whether we're a fit. If not, you've lost 20 minutes, not a quarter.\n\n"
        f"Does sometime next week work?{cal}\n\n"
        f"Best,\n{config.FROM_NAME}\n{config.SENDER_COMPANY}"
    )
    return {"subject": subject, "body": body}


def compose(lead: dict, icp: dict) -> dict:
    return _llm_compose(lead, icp) or _template_compose(lead, icp)
