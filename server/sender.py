"""Stage 04 — send email.

Real SMTP when configured. Otherwise messages are parked in the outbox
(status='queued_outbox') — honestly labeled, never marked 'sent'.
"""

from __future__ import annotations

import smtplib
import time
from email.message import EmailMessage

from . import config


def send_one(to_addr: str, subject: str, body: str) -> dict:
    """Returns {'status': 'sent'|'queued_outbox', 'provider_msg_id': str}."""
    if not (config.SMTP_HOST and config.SMTP_USER and config.SMTP_PASS):
        return {"status": "queued_outbox", "provider_msg_id": ""}

    msg = EmailMessage()
    msg["From"] = f"{config.FROM_NAME} <{config.FROM_EMAIL}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(config.SMTP_USER, config.SMTP_PASS)
        smtp.send_message(msg)
    return {"status": "sent", "provider_msg_id": msg["Message-ID"] or ""}


def throttle() -> None:
    if config.SEND_DELAY_SECONDS > 0:
        time.sleep(config.SEND_DELAY_SECONDS)
