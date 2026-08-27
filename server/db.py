"""SQLite persistence layer. Single connection per call — no ORM, no magic."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    product TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(id),
    stage TEXT NOT NULL,
    message TEXT NOT NULL,
    ts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT '',
    title TEXT DEFAULT '',
    company TEXT DEFAULT '',
    domain TEXT DEFAULT '',
    country TEXT DEFAULT '',
    industry TEXT DEFAULT '',
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(id),
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    provider_msg_id TEXT DEFAULT '',
    sent_at TEXT
);
CREATE TABLE IF NOT EXISTS replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL REFERENCES emails(id),
    body TEXT NOT NULL,
    intent TEXT NOT NULL,
    received_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meetings (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    title TEXT NOT NULL,
    start_iso TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    ics_path TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'proposed',
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def log_event(conn: sqlite3.Connection, run_id: str, stage: str, message: str) -> None:
    conn.execute(
        "INSERT INTO run_events (run_id, stage, message, ts) VALUES (?,?,?,?)",
        (run_id, stage, message, _now()),
    )
    conn.commit()


def set_run_status(conn: sqlite3.Connection, run_id: str, status: str, finished: bool = False) -> None:
    conn.execute(
        "UPDATE runs SET status=?, finished_at=? WHERE id=?",
        (status, _now() if finished else None, run_id),
    )
    conn.commit()


def upsert_lead(conn: sqlite3.Connection, lead: dict) -> int:
    conn.execute(
        """INSERT INTO leads (email, first_name, last_name, title, company, domain, country, industry, source, created_at)
           VALUES (:email, :first_name, :last_name, :title, :company, :domain, :country, :industry, :source, :created_at)
           ON CONFLICT(email) DO UPDATE SET
             first_name=excluded.first_name, last_name=excluded.last_name, title=excluded.title,
             company=excluded.company, domain=excluded.domain, country=excluded.country,
             industry=excluded.industry, source=excluded.source""",
        {**lead, "created_at": _now()},
    )
    row = conn.execute("SELECT id FROM leads WHERE email=?", (lead["email"],)).fetchone()
    conn.commit()
    return row["id"]


def get_run(conn: sqlite3.Connection, run_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        return None
    run = dict(row)
    run["config"] = json.loads(run.pop("config_json") or "{}")
    run["events"] = [
        dict(r)
        for r in conn.execute(
            "SELECT stage, message, ts FROM run_events WHERE run_id=? ORDER BY id", (run_id,)
        ).fetchall()
    ]
    run["meetings"] = [
        dict(r)
        for r in conn.execute(
            """SELECT m.id, m.title, m.start_iso, m.timezone, m.status,
                      l.first_name, l.last_name, l.title AS lead_title, l.company, l.country
               FROM meetings m JOIN leads l ON l.id = m.lead_id
               WHERE m.run_id=? ORDER BY m.created_at""",
            (run_id,),
        ).fetchall()
    ]
    run["emails_sent"] = conn.execute(
        "SELECT COUNT(*) c FROM emails WHERE run_id=? AND status IN ('sent','queued_outbox')", (run_id,)
    ).fetchone()["c"]
    run["leads_found"] = conn.execute(
        "SELECT COUNT(DISTINCT lead_id) c FROM emails WHERE run_id=?", (run_id,)
    ).fetchone()["c"]
    return run
