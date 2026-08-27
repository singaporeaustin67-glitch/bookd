# AGENTS.md

## Project: BOOKD — meeting-delivery engine landing page
Static marketing site for a "Workflow AI over Data" acquisition service: database lives in the
backend vault, frontend sells fully-booked meetings as the deliverable. Language: English.

## Files
- `index.html` — single page (Hero / contrast / 5-stage pipeline / live demo widget / pricing / FAQ)
- `styles.css` — industrial dispatch aesthetic: ink black, safety orange, cream paper, lime accent
- `script.js` — terminal pipeline sim, ticker, scroll reveals, count-up stats, demo widget

## Local preview
`python3 -m http.server 12000`

## Fonts
Playfair Display (serif headlines) + Inter (body) + Archivo Black (logo) + JetBrains Mono (labels/terminal).
Note: the mono stack previously needed a CJK fallback (`"Noto Sans TC"`) — removed when the site went
English-only; re-add if Chinese copy returns or tofu boxes appear.
