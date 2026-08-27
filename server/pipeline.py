"""Run orchestrator: ICP → source → compose → send, with an event log per run."""

from __future__ import annotations

from datetime import datetime, timezone

from . import booker, classify, compose, config, db, icp as icp_mod, sender
from .providers import source_leads


def execute_run(run_id: str, product: str, overrides: dict, send: bool) -> None:
    conn = db.connect()
    try:
        db.set_run_status(conn, run_id, "running")

        # 01 — ICP
        profile = icp_mod.build_icp(product, overrides)
        db.log_event(conn, run_id, "input", f"ICP locked: titles={len(profile['titles'])}, keywords={', '.join(profile['keywords'][:5])}")

        # 02 — source
        leads, notes = source_leads(profile, config.MAX_LEADS_PER_RUN)
        for note in notes:
            db.log_event(conn, run_id, "search", note)
        if not leads:
            db.log_event(conn, run_id, "search", "No leads available from any configured source.")
            db.set_run_status(conn, run_id, "no_leads", finished=True)
            return
        db.log_event(conn, run_id, "search", f"{len(leads)} buyers matched")

        # 03+04 — compose & send/queue
        sent = 0
        for lead in leads:
            lead_id = db.upsert_lead(conn, lead)
            draft = compose.compose(lead, profile)
            cur = conn.execute(
                "INSERT INTO emails (run_id, lead_id, subject, body, status) VALUES (?,?,?,?,?)",
                (run_id, lead_id, draft["subject"], draft["body"], "draft"),
            )
            email_id = cur.lastrowid
            if send:
                result = sender.send_one(lead["email"], draft["subject"], draft["body"])
                conn.execute(
                    "UPDATE emails SET status=?, provider_msg_id=?, sent_at=? WHERE id=?",
                    (result["status"], result["provider_msg_id"], datetime.now(timezone.utc).isoformat(timespec="seconds"), email_id),
                )
                sent += 1
                sender.throttle()
            conn.commit()
        mode = "SMTP" if config.capabilities()["smtp_configured"] else "outbox (SMTP not configured)"
        if send:
            db.log_event(conn, run_id, "send", f"{sent} emails dispatched via {mode}")
        else:
            db.log_event(conn, run_id, "write", f"{len(leads)} personalized drafts prepared (send=False — review first)")

        db.set_run_status(conn, run_id, "completed", finished=True)
    except Exception as exc:
        db.log_event(conn, run_id, "error", str(exc))
        db.set_run_status(conn, run_id, "failed", finished=True)
    finally:
        conn.close()


def handle_reply(conn, email_row, body: str) -> dict:
    """Classify a reply; if positive, book a meeting and emit a real .ics."""
    intent = classify.classify(body)
    conn.execute(
        "INSERT INTO replies (email_id, body, intent, received_at) VALUES (?,?,?,?)",
        (email_row["id"], body, intent, datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )
    conn.commit()

    result = {"intent": intent, "meeting_id": None}
    if intent != "positive":
        return result

    lead = conn.execute("SELECT * FROM leads WHERE id=?", (email_row["lead_id"],)).fetchone()
    run = conn.execute("SELECT * FROM runs WHERE id=?", (email_row["run_id"],)).fetchone()
    requested = booker.extract_requested_time(body)
    proposal = booker.propose_meeting(dict(lead), run["product"], after=requested)
    start = requested or proposal["start"]

    meeting_id = db.new_id()
    ics_file = booker.write_ics(meeting_id, proposal["title"], start, lead["email"])
    conn.execute(
        """INSERT INTO meetings (id, run_id, lead_id, title, start_iso, timezone, ics_path, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            meeting_id, run["id"], lead["id"], proposal["title"],
            start.isoformat(timespec="seconds"), "UTC", ics_file, "booked",
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    db.log_event(conn, run["id"], "booked", f"Meeting booked with {lead['company'] or lead['email']} — {start.isoformat(timespec='seconds')}")
    conn.commit()
    result["meeting_id"] = meeting_id
    return result
