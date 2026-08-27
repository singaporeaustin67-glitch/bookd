"""Provider registry: ordered by preference, first available-with-results wins."""

from __future__ import annotations

from .apollo import ApolloProvider
from .local import LocalProvider

PROVIDERS = [ApolloProvider(), LocalProvider()]


def source_leads(icp: dict, limit: int) -> tuple[list[dict], list[str]]:
    """Returns (leads, notes). Notes explain what happened, honestly."""
    notes: list[str] = []
    for provider in PROVIDERS:
        if not provider.available():
            notes.append(f"{provider.name}: skipped (not configured)")
            continue
        try:
            leads = provider.search(icp, limit)
        except Exception as exc:  # provider outage shouldn't kill the run
            notes.append(f"{provider.name}: error — {exc}")
            continue
        if leads:
            notes.append(f"{provider.name}: {len(leads)} leads")
            return leads, notes
        notes.append(f"{provider.name}: 0 leads")
    return [], notes
