"""BOOKD engine — FastAPI application. Serves the API and the static site."""

from __future__ import annotations

import csv
import io
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, pipeline
from .models import ContactIn, LeadIn, ReplyIn, RunRequest

ROOT = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="BOOKD Engine", version="0.1.0", lifespan=lifespan)


@app.get("/api/config")
def get_config() -> dict:
    return config.capabilities()


@app.post("/api/runs", status_code=201)
def create_run(req: RunRequest, background: BackgroundTasks) -> dict:
    run_id = db.new_id()
    overrides = {
        "target_titles": req.target_titles,
        "target_countries": req.target_countries,
        "target_industries": req.target_industries,
    }
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO runs (id, product, status, config_json, created_at) VALUES (?,?,?,?,?)",
            (run_id, req.product, "queued", "{}", datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        conn.commit()
    background.add_task(pipeline.execute_run, run_id, req.product, overrides, req.send)
    return {"run_id": run_id, "status": "queued"}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict:
    with db.connect() as conn:
        run = db.get_run(conn, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run


@app.post("/api/leads/import", status_code=201)
async def import_leads(file: UploadFile) -> dict:
    """Import your own leads as CSV. Columns: email,first_name,last_name,title,company,domain,country,industry"""
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames or "email" not in [f.strip().lower() for f in reader.fieldnames]:
        raise HTTPException(400, "CSV must include an 'email' column")
    imported, skipped = 0, 0
    with db.connect() as conn:
        for row in reader:
            row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
            if "@" not in row.get("email", ""):
                skipped += 1
                continue
            db.upsert_lead(conn, {f: row.get(f, "") for f in
                                  ("email", "first_name", "last_name", "title", "company", "domain", "country", "industry")} | {"source": "csv_import"})
            imported += 1
    return {"imported": imported, "skipped": skipped}


@app.post("/api/leads", status_code=201)
def add_lead(lead: LeadIn) -> dict:
    if "@" not in lead.email:
        raise HTTPException(400, "valid email required")
    with db.connect() as conn:
        lead_id = db.upsert_lead(conn, lead.model_dump() | {"source": "api"})
    return {"lead_id": lead_id}


@app.post("/api/replies", status_code=201)
def ingest_reply(reply: ReplyIn) -> dict:
    """Inbound webhook: point your mail provider's inbound-parse here."""
    with db.connect() as conn:
        email_row = None
        if reply.email_id:
            email_row = conn.execute("SELECT * FROM emails WHERE id=?", (reply.email_id,)).fetchone()
        elif reply.from_email:
            email_row = conn.execute(
                """SELECT e.* FROM emails e JOIN leads l ON l.id = e.lead_id
                   WHERE l.email = ? ORDER BY e.id DESC LIMIT 1""",
                (reply.from_email,),
            ).fetchone()
        if not email_row:
            raise HTTPException(404, "no matching outbound email found")
        return pipeline.handle_reply(conn, email_row, reply.body)


@app.get("/api/stats")
def stats() -> dict:
    """Live numbers from the engine's own database — nothing invented."""
    with db.connect() as conn:
        one = lambda q: conn.execute(q).fetchone()[0]
        return {
            "leads": one("SELECT COUNT(*) FROM leads"),
            "emails_sent": one("SELECT COUNT(*) FROM emails WHERE status IN ('sent','queued_outbox')"),
            "drafts": one("SELECT COUNT(*) FROM emails WHERE status='draft'"),
            "meetings": one("SELECT COUNT(*) FROM meetings"),
            "runs": one("SELECT COUNT(*) FROM runs"),
        }


@app.get("/api/meetings")
def list_meetings() -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT m.*, l.email AS lead_email, l.company, l.first_name, l.last_name
               FROM meetings m JOIN leads l ON l.id = m.lead_id ORDER BY m.created_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/meetings/{meeting_id}/ics")
def download_ics(meeting_id: str) -> FileResponse:
    with db.connect() as conn:
        row = conn.execute("SELECT ics_path FROM meetings WHERE id=?", (meeting_id,)).fetchone()
    if not row or not row["ics_path"]:
        raise HTTPException(404, "meeting not found")
    path = config.MEETINGS_DIR / row["ics_path"]
    if not path.exists():
        raise HTTPException(404, "ics file missing")
    return FileResponse(path, media_type="text/calendar", filename=row["ics_path"])


@app.post("/api/contacts", status_code=201)
def add_contact(contact: ContactIn) -> dict:
    if "@" not in contact.email:
        raise HTTPException(400, "valid email required")
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO contacts (name, email, product, created_at) VALUES (?,?,?,?)",
            (contact.name.strip(), contact.email.strip(), contact.product.strip(),
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        conn.commit()
    return {"contact_id": cur.lastrowid, "status": "received"}


@app.get("/api/contacts")
def list_contacts() -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM contacts ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


# Static site last — API routes take precedence
app.mount("/", StaticFiles(directory=ROOT, html=True), name="site")
