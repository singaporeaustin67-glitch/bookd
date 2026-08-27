"""Monthly hunt quota — counts leads sourced per workspace per month."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import db, tiers


class QuotaExceeded(Exception):
    def __init__(self, tier: str, limit: int):
        super().__init__(f"{tier} plan monthly hunt quota ({limit}) reached")
        self.tier = tier
        self.limit = limit


def month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def current_tier(conn: sqlite3.Connection, workspace: str = tiers.DEFAULT_WORKSPACE) -> str:
    row = conn.execute("SELECT tier FROM workspace WHERE id=?", (workspace,)).fetchone()
    return row["tier"] if row else "free"


def set_tier(conn: sqlite3.Connection, tier: str, workspace: str = tiers.DEFAULT_WORKSPACE) -> str:
    tiers.tier_info(tier)  # validate
    conn.execute(
        """INSERT INTO workspace (id, tier, created_at) VALUES (?,?,?)
           ON CONFLICT(id) DO UPDATE SET tier=excluded.tier""",
        (workspace, tier, db._now()),
    )
    conn.commit()
    return tier


def usage(conn: sqlite3.Connection, workspace: str = tiers.DEFAULT_WORKSPACE) -> int:
    row = conn.execute(
        "SELECT hunts FROM usage_counters WHERE workspace=? AND month=?",
        (workspace, month_key()),
    ).fetchone()
    return row["hunts"] if row else 0


def status(conn: sqlite3.Connection, workspace: str = tiers.DEFAULT_WORKSPACE) -> dict:
    tier = current_tier(conn, workspace)
    info = tiers.tier_info(tier)
    used = usage(conn, workspace)
    limit = info["hunt_limit"]
    return {
        "tier": tier,
        "label": info["label"],
        "month": month_key(),
        "used": used,
        "limit": limit,
        "remaining": None if limit is None else max(limit - used, 0),
    }


def check(conn: sqlite3.Connection, workspace: str = tiers.DEFAULT_WORKSPACE) -> dict:
    """Raise QuotaExceeded when the month's allowance is spent."""
    state = status(conn, workspace)
    if state["remaining"] == 0:
        raise QuotaExceeded(state["tier"], state["limit"])
    return state


def cap_request(conn: sqlite3.Connection, requested: int, workspace: str = tiers.DEFAULT_WORKSPACE) -> tuple[int, bool]:
    """Reduce the requested limit to what's left this month. Returns (limit, capped)."""
    state = check(conn, workspace)
    if state["remaining"] is None:
        return requested, False
    allowed = min(requested, state["remaining"])
    return allowed, allowed < requested


def consume(conn: sqlite3.Connection, count: int, workspace: str = tiers.DEFAULT_WORKSPACE) -> int:
    if count <= 0:
        return usage(conn, workspace)
    conn.execute(
        """INSERT INTO usage_counters (workspace, month, hunts) VALUES (?,?,?)
           ON CONFLICT(workspace, month) DO UPDATE SET hunts = hunts + excluded.hunts""",
        (workspace, month_key(), count),
    )
    conn.commit()
    return usage(conn, workspace)
