# AGENTS.md

## Project: BOOKD — subscription SaaS meeting-delivery engine (landing page + real backend)
"Workflow AI over Data" acquisition product: the lead database stays in the vault, the deliverable
sold is booked meetings — billed as a flat monthly subscription, not per meeting. Language: English.
No mock/simulated anything — the frontend reads only what the engine's database returns.

## Tiers (server/tiers.py — the source of truth)
- `free`      — $0,  50 hunts/month
- `professional` — $79/mo ($59 annual), 3,000 hunts/month
- `enterprise` — $499+/mo scoped, unlimited hunts

## Subscription machinery (server/quota.py + server/keys.py)
- Usage counters keyed by (workspace, month); sourcing a lead consumes one hunt. Run creation
  returns HTTP 402 with a JSON detail when the month's allowance is spent; the run's source stage
  caps the requested limit to what remains and logs "capped".
- BYOK: Apollo/Hunter keys are entered into the workspace (POST /api/workspace/keys), Fernet-
  encrypted at rest with the master key from `BOOKD_SECRET_KEY` (falls back to a generated key in
  `data/.secret_key`). Providers resolve BYOK first, env vars second. `/api/config` reports the
  provider source (`byok` / `env` / `none`).
- `PUT /api/workspace/tier` flips the plan — demo admin only; in production a Stripe webhook owns
  tier changes. Never trust a client-provided tier in a request.
- `GET /api/workspace` returns quota, stored key previews, and the plan catalog.

## Layout
- `index.html` / `styles.css` / `script.js` — landing page (hero, contrast, 5-stage pipeline, live demo, pricing, FAQ)
- `server/` — FastAPI engine:
  - `app.py` — API + static serving; `config.py` — env/.env config; `db.py` — SQLite
  - `pipeline.py` — run orchestrator; `icp.py` — buyer profile extraction
  - `tiers.py` / `quota.py` / `keys.py` — plans, monthly usage, BYOK vault
  - `providers/` — local CSV-imported leads (always on) + Apollo/Hunter adapters (resolve BYOK first)
  - `compose.py` — LLM writer (OpenAI/Anthropic) with template fallback; `sender.py` — SMTP/outbox
  - `classify.py` — reply intent; `booker.py` — time extraction + real .ics files
- `tests/test_engine.py` — pytest end-to-end (import → run → reply → booked .ics, contact capture, BYOK lifecycle, quota cap/block/upgrade). 15 tests, all real code paths.
- `data/` — runtime SQLite + .ics + `.secret_key` (gitignored); `.env` — secrets (gitignored, never commit)

## Run
- `python3 -m uvicorn server.app:app --host 0.0.0.0 --port 12000` (API + site together)
- `python3 -m pytest tests/ -q`
- Go-live switches: `APOLLO_API_KEY`, `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`, `SMTP_*`, `BOOKD_SECRET_KEY` in `.env`.
  `/api/config` honestly reports which subsystems are live (composer / sender / provider sources).

## Design
Ink black + safety orange + cream paper + lime accent; Playfair Display headlines, Inter body,
Archivo Black logo, JetBrains Mono labels. (CJK fallback was removed when the site went English;
re-add `"Noto Sans TC"` if Chinese copy returns or tofu boxes appear.)

