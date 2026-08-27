"""End-to-end tests against the real app, real SQLite, real pipeline.

No mocks. The only external systems (SMTP, Apollo, LLM) are exercised through
their honest fallback paths: outbox mode, local provider, template composer.
"""

from __future__ import annotations

import os
import time

import pytest
from fastapi.testclient import TestClient

# Isolated DB per test session, before config is imported
os.environ["BOOKD_DB"] = "/tmp/bookd_test.db"
if os.path.exists("/tmp/bookd_test.db"):
    os.remove("/tmp/bookd_test.db")

from server import booker, classify, db, icp, keys, quota  # noqa: E402
from server.app import app  # noqa: E402

db.init_db()
client = TestClient(app)

LEADS_CSV = """email,first_name,last_name,title,company,domain,country,industry
j.weber@precisionparts.example,Jonas,Weber,Sourcing Director,Precision Parts GmbH,precisionparts.example,Germany,Manufacturing
a.silva@novacorp.example,Ana,Silva,VP Procurement,NovaCorp,novacorp.example,Brazil,Construction
kenji@yamamoto-ind.example,Kenji,Sato,Purchasing Manager,Yamamoto Industries,yamamoto-ind.example,Japan,Automotive
"""


def test_contact_capture():
    resp = client.post(
        "/api/contacts",
        json={"name": "Ada", "email": "ada@buyer.example", "product": "EV fleet BMS"},
    )
    assert resp.status_code == 201
    listed = client.get("/api/contacts").json()
    assert listed[0]["email"] == "ada@buyer.example"


def test_icp_extraction():
    profile = icp.build_icp("Industrial CNC cutting fluid for aerospace machining")
    assert "cutting" in profile["keywords"] or "fluid" in profile["keywords"]
    assert profile["titles"]  # default buyer titles present


def test_classifier_intents():
    assert classify.classify("This sounds good, let's talk next week") == "positive"
    assert classify.classify("Not interested, please remove me") == "negative"
    assert classify.classify("How much does it cost?") == "question"
    assert classify.classify("Got it, thanks") == "neutral"


def test_time_extraction():
    dt = booker.extract_requested_time("Can we do Tuesday 3pm?")
    assert dt is not None and dt.weekday() == 1 and dt.hour == 15
    assert booker.extract_requested_time("sounds great") is None


def test_config_reports_honest_capabilities():
    caps = client.get("/api/config").json()
    assert caps["lead_providers"]["csv_import"] is True
    assert caps["sender"] in ("smtp", "outbox_only")


def test_import_leads_csv():
    resp = client.post(
        "/api/leads/import",
        files={"file": ("leads.csv", LEADS_CSV, "text/csv")},
    )
    assert resp.status_code == 201
    assert resp.json()["imported"] == 3


def test_full_run_draft_mode():
    resp = client.post("/api/runs", json={"product": "CNC cutting fluid", "send": False})
    assert resp.status_code == 201
    run_id = resp.json()["run_id"]

    run = _wait_for_run(run_id)
    assert run["status"] == "completed"
    assert run["leads_found"] == 3
    stages = [e["stage"] for e in run["events"]]
    assert "input" in stages and "search" in stages and "write" in stages


def test_full_run_send_mode_outbox():
    resp = client.post("/api/runs", json={"product": "CNC cutting fluid", "send": True})
    run_id = resp.json()["run_id"]
    run = _wait_for_run(run_id)
    assert run["status"] == "completed"
    # SMTP not configured in test env → honestly queued, never faked as sent
    assert run["emails_sent"] == 3
    with db.connect() as conn:
        rows = conn.execute("SELECT DISTINCT status FROM emails WHERE run_id=?", (run_id,)).fetchall()
    assert {r["status"] for r in rows} == {"queued_outbox"}


def test_reply_positive_books_meeting_with_real_ics():
    with db.connect() as conn:
        email_row = conn.execute("SELECT * FROM emails ORDER BY id LIMIT 1").fetchone()
    resp = client.post(
        "/api/replies",
        json={"email_id": email_row["id"], "body": "Sounds good — can we do Tuesday 3pm?"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["intent"] == "positive"
    assert data["meeting_id"]

    ics = client.get(f"/api/meetings/{data['meeting_id']}/ics")
    assert ics.status_code == 200
    assert "BEGIN:VCALENDAR" in ics.text
    assert "DTSTART" in ics.text

    run = client.get(f"/api/runs/{email_row['run_id']}").json()
    assert any(e["stage"] == "booked" for e in run["events"])
    assert len(run["meetings"]) == 1


def test_reply_negative_books_nothing():
    with db.connect() as conn:
        email_row = conn.execute("SELECT * FROM emails ORDER BY id DESC LIMIT 1").fetchone()
    resp = client.post(
        "/api/replies",
        json={"email_id": email_row["id"], "body": "Not interested, remove me please."},
    )
    assert resp.json() == {"intent": "negative", "meeting_id": None}


def test_reply_from_unknown_sender_404():
    resp = client.post("/api/replies", json={"from_email": "ghost@nowhere.example", "body": "hi"})
    assert resp.status_code == 404


def _wait_for_run(run_id: str, timeout: float = 15) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] in ("completed", "failed", "no_leads", "quota_exceeded"):
            return run
        time.sleep(0.2)
    pytest.fail(f"run {run_id} did not finish in {timeout}s")


def test_workspace_defaults_to_free_tier():
    data = client.get("/api/workspace").json()
    assert data["quota"]["tier"] == "free"
    assert data["quota"]["limit"] == 50
    assert data["plans"]["professional"]["hunt_limit"] == 3000


def test_byok_key_lifecycle():
    resp = client.post(
        "/api/workspace/keys",
        json={"provider": "apollo", "api_key": "test-apollo-secret-1234"},
    )
    assert resp.status_code == 201
    assert resp.json()["preview"] == "····1234"

    ws = client.get("/api/workspace").json()
    assert ws["keys"][0]["provider"] == "apollo"
    assert "test" not in ws["keys"][0]["preview"]

    key, source = keys.resolve("apollo")
    assert key == "test-apollo-secret-1234"
    assert source == "byok"

    assert client.delete("/api/workspace/keys/apollo").json() == {"deleted": "apollo"}
    key, source = keys.resolve("apollo")
    assert key is None and source in ("env", "none")


def test_quota_caps_then_blocks_runs():
    # burn the free allowance down to one hunt left
    with db.connect() as conn:
        conn.execute(
            "DELETE FROM usage_counters WHERE workspace=? AND month=?",
            ("local", quota.month_key()),
        )
        conn.commit()
        quota.consume(conn, 49)
    resp = client.post("/api/runs", json={"product": "quota cap test", "send": False})
    assert resp.status_code == 201
    run = _wait_for_run(resp.json()["run_id"])
    assert run["status"] == "completed"
    assert run["leads_found"] == 1  # request capped by what this month has left
    assert any("capped" in e["message"] for e in run["events"])
    with db.connect() as conn:
        assert quota.usage(conn) == 50

    # quota spent → 402, run never created
    resp = client.post("/api/runs", json={"product": "blocked", "send": False})
    assert resp.status_code == 402
    assert resp.json()["detail"]["error"] == "quota_exceeded"

    # upgrading flips it open again
    assert client.put("/api/workspace/tier", json={"tier": "professional"}).status_code == 200
    resp = client.post("/api/runs", json={"product": "post-upgrade", "send": False})
    assert resp.status_code == 201
    run = _wait_for_run(resp.json()["run_id"])
    assert run["status"] == "completed"
    assert run["leads_found"] == 3
    # restore defaults for future tests
    assert client.put("/api/workspace/tier", json={"tier": "free"}).status_code == 200
