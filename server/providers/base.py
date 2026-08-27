"""Lead provider interface. Every provider returns plain dicts with a common shape."""

from __future__ import annotations

from typing import Protocol

LEAD_FIELDS = ("email", "first_name", "last_name", "title", "company", "domain", "country", "industry")


class LeadProvider(Protocol):
    name: str

    def available(self) -> bool: ...

    def search(self, icp: dict, limit: int) -> list[dict]: ...


def normalize(raw: dict, source: str) -> dict:
    lead = {f: (raw.get(f) or "").strip() for f in LEAD_FIELDS}
    lead["source"] = source
    return lead
