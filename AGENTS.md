# AGENTS.md

## Project: BOOKD — meeting-delivery engine (landing page + real backend)
"Workflow AI over Data" acquisition product: the lead database stays in the vault, the deliverable
sold is booked meetings. Language: English. No mock/simulated anything — the frontend reads only
what the engine's database returns.

## Layout
- `index.html` / `styles.css` / `script.js` — landing page (hero, contrast, 5-stage pipeline, live demo, pricing, FAQ)
- `server/` — FastAPI engine:
  - `app.py` — API + static serving; `config.py` — env/.env config; `db.py` — SQLite
  - `pipeline.py` — run orchestrator; `icp.py` — buyer profile extraction
  - `providers/` — local CSV-imported leads (always on) + Apollo/Hunter adapters (activate with keys)
  - `compose.py` — LLM writer (OpenAI/Anthropic) with template fallback; `sender.py` — SMTP/outbox
  - `classify.py` — reply intent; `booker.py` — time extraction + real .ics files
- `tests/test_engine.py` — pytest end-to-end (import → run → reply → booked .ics, contact capture). 11 tests, all real code paths.
- `data/` — runtime SQLite + .ics files (gitignored); `.env` — secrets (gitignored, never commit)

## Run
- `python3 -m uvicorn server.app:app --host 0.0.0.0 --port 12000` (API + site together)
- `python3 -m pytest tests/ -q`
- Go-live switches: `APOLLO_API_KEY`, `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`, `SMTP_*` in `.env`.
  `/api/config` honestly reports which subsystems are live (composer / sender / providers).

## Design
Ink black + safety orange + cream paper + lime accent; Playfair Display headlines, Inter body,
Archivo Black logo, JetBrains Mono labels. (CJK fallback was removed when the site went English;
re-add `"Noto Sans TC"` if Chinese copy returns or tofu boxes appear.)

