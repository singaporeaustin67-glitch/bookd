"""Stage 05b — booking. Produces real RFC 5545 .ics files you can import anywhere."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

from . import config

DURATION_MINUTES = 20


def _next_business_slot(after: datetime | None = None) -> datetime:
    """Next weekday at 10:00 UTC, skipping weekends."""
    dt = (after or datetime.now(timezone.utc)) + timedelta(days=1)
    dt = dt.replace(hour=10, minute=0, second=0, microsecond=0)
    while dt.weekday() >= 5:
        dt += timedelta(days=1)
    return dt


def propose_meeting(lead: dict, product: str, after: datetime | None = None) -> dict:
    start = _next_business_slot(after)
    return {
        "title": f"{product.split(',')[0].strip()[:50]} — intro call ({lead['company'] or lead['email']})",
        "start": start,
        "timezone": "UTC",
    }


def extract_requested_time(body: str) -> datetime | None:
    """Very small parser: 'tuesday 3pm', 'thu 15:00' style hints → next occurrence (UTC)."""
    text = body.lower()
    weekdays = {
        "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "wednesday": 2, "wed": 2,
        "thursday": 3, "thu": 3, "friday": 4, "fri": 4,
    }
    day = next((d for name, d in weekdays.items() if re.search(rf"\b{name}\b", text)), None)
    if day is None:
        return None
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text)
    hour = 10
    minute = 0
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        if m.group(3) == "pm" and hour < 12:
            hour += 12
        if m.group(3) == "am" and hour == 12:
            hour = 0
    now = datetime.now(timezone.utc)
    days_ahead = (day - now.weekday()) % 7 or 7
    return (now + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0, microsecond=0)


def write_ics(meeting_id: str, title: str, start: datetime, attendee_email: str) -> str:
    """Writes the .ics file, returns its path relative to the meetings dir."""
    config.MEETINGS_DIR.mkdir(parents=True, exist_ok=True)
    end = start + timedelta(minutes=DURATION_MINUTES)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fmt = "%Y%m%dT%H%M%SZ"
    ics = "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//BOOKD//Meeting Engine//EN",
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}@bookd",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{start.strftime(fmt)}",
            f"DTEND:{end.strftime(fmt)}",
            f"SUMMARY:{title}",
            f"ATTENDEE;CN={attendee_email}:mailto:{attendee_email}",
            f"ORGANIZER;CN={config.FROM_NAME}:mailto:{config.FROM_EMAIL or 'noreply@bookd.local'}",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )
    filename = f"{meeting_id}.ics"
    (config.MEETINGS_DIR / filename).write_text(ics)
    return filename
