/* BOOKD — frontend wired to the real engine API.
   The demo widget creates actual runs in the backend and renders what the
   database returns. Nothing on this page is scripted anymore. */

(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── status bar: honest capability report from the engine ── */
  const statusText = document.querySelector(".statusbar-text");
  fetch("/api/config")
    .then((r) => r.json())
    .then((caps) => {
      const providers = Object.entries(caps.lead_providers)
        .filter(([, on]) => on)
        .map(([name]) => name)
        .join(" + ");
      statusText.textContent =
        `ENGINE ONLINE — composer: ${caps.composer} · sender: ${caps.sender} · sources: ${providers}`;
    })
    .catch(() => {
      statusText.textContent = "ENGINE OFFLINE — API unreachable";
    });

  /* ── hero terminal: shows real booked meetings, or the honest empty state ── */
  const log = document.getElementById("terminalLog");
  const result = document.getElementById("terminalResult");
  fetch("/api/meetings")
    .then((r) => r.json())
    .then((meetings) => {
      if (!meetings.length) {
        log.innerHTML = "<li>No meetings booked yet — run the engine below.</li>";
        return;
      }
      meetings.slice(0, 5).forEach((m, i) => {
        setTimeout(() => {
          const li = document.createElement("li");
          li.classList.add("ok");
          li.textContent = `${m.company || m.lead_email} — ${m.start_iso} UTC`;
          log.appendChild(li);
        }, i * (reduceMotion ? 10 : 400));
      });
      result.textContent = `✔ ${meetings.length} meeting${meetings.length > 1 ? "s" : ""} on the calendar`;
      result.hidden = false;
    })
    .catch(() => {
      log.innerHTML = "<li>Engine offline.</li>";
    });

  /* ── ticker ─────────────────────────────────────────────── */
  const lines = [
    "✔ RESULT, NOT DATA",
    "✔ YOU PAY FOR MET MEETINGS",
    "✔ NO-SHOW = NO CHARGE",
    "✔ THE LIST NEVER LEAVES THE VAULT",
    "✔ QUALITY GATE BEFORE EVERY SEND",
    "✔ MEETINGS. THAT'S THE DELIVERABLE.",
  ];
  const track = document.getElementById("tickerTrack");
  if (track) {
    const items = lines.map((t) => `<span>${t}</span>`).join("");
    track.innerHTML = items + items;
  }

  /* ── scroll reveals ─────────────────────────────────────── */
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          io.unobserve(e.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  document.querySelectorAll(".reveal").forEach((el) => io.observe(el));

  /* ── live stats from the engine DB ────────────────────── */
  fetch("/api/stats")
    .then((r) => r.json())
    .then((s) => {
      const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
      set("statLeads", s.leads);
      set("statEmails", s.emails_sent);
      set("statMeetings", s.meetings);
      set("statRuns", s.runs);
    })
    .catch(() => {});

  /* ── hero form → demo section ───────────────────────────── */
  const heroForm = document.getElementById("heroForm");
  const heroInput = document.getElementById("heroInput");
  const demoInput = document.getElementById("demoInput");
  heroForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    if (heroInput.value.trim()) demoInput.value = heroInput.value.trim();
    document.getElementById("demo").scrollIntoView({ behavior: "smooth" });
  });

  /* ── demo widget: real runs against the engine ──────────── */
  const demoForm = document.getElementById("demoForm");
  const stepsBox = document.getElementById("demoSteps");
  const resultsBox = document.getElementById("demoResults");
  const countEl = resultsBox.querySelector(".demo__count");
  const cardsEl = resultsBox.querySelector(".demo__cards");

  const STAGE_ORDER = ["input", "search", "write", "send", "booked"];

  function renderEvents(events) {
    stepsBox.innerHTML = "";
    events.forEach((ev) => {
      const li = document.createElement("li");
      li.classList.add("done");
      const idx = STAGE_ORDER.indexOf(ev.stage);
      li.innerHTML = `<i>${String(idx + 1).padStart(2, "0")}</i> ${ev.message}`;
      stepsBox.appendChild(li);
    });
  }

  function renderMeetings(meetings) {
    cardsEl.innerHTML = "";
    meetings.forEach((m) => {
      const card = document.createElement("article");
      card.className = "meet-card";
      const name = [m.first_name, m.last_name].filter(Boolean).join(" ") || m.lead_title || "Buyer";
      card.innerHTML = `
        <h4>${name}</h4><p class="mono">${(m.lead_title || "").toUpperCase()}</p>
        <p class="meet-card__org">${m.company || ""}${m.country ? " · " + m.country : ""}</p>
        <p class="meet-card__time mono">${m.start_iso} UTC</p>
        <a class="meet-card__ics mono" href="/api/meetings/${m.id}/ics" download>↓ add to calendar (.ics)</a>`;
      cardsEl.appendChild(card);
    });
  }

  async function pollRun(runId) {
    const resp = await fetch(`/api/runs/${runId}`);
    const run = await resp.json();
    renderEvents(run.events);

    if (["completed", "failed", "no_leads"].includes(run.status)) {
      resultsBox.hidden = false;
      if (run.status === "no_leads") {
        countEl.innerHTML =
          "✕ No leads in any configured source. Import your own list: " +
          "<code>POST /api/leads/import</code> (CSV) or set <code>APOLLO_API_KEY</code>.";
        cardsEl.innerHTML = "";
      } else if (run.status === "failed") {
        countEl.textContent = "✕ Run failed — see the event log above.";
        cardsEl.innerHTML = "";
      } else if (run.meetings.length) {
        countEl.innerHTML = `✔ <b>${run.meetings.length}</b> meeting${run.meetings.length > 1 ? "s" : ""} booked`;
        renderMeetings(run.meetings);
      } else {
        const sentPart = run.emails_sent
          ? ` ${run.emails_sent} emails queued/sent.`
          : " Drafts prepared (send=false).";
        countEl.innerHTML =
          `✔ Run complete — ${run.leads_found} buyers matched.${sentPart} ` +
          "Meetings appear here when buyers reply.";
        cardsEl.innerHTML = "";
      }
      return;
    }
    setTimeout(() => pollRun(runId), 700);
  }

  demoForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const product = demoInput.value.trim();
    if (!product) return;
    resultsBox.hidden = true;
    stepsBox.innerHTML = "<li class='active'><i>01</i> Starting run…</li>";
    try {
      const resp = await fetch("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product, send: false }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const { run_id } = await resp.json();
      pollRun(run_id);
    } catch (err) {
      stepsBox.innerHTML = `<li class='active'><i>!!</i> Engine unreachable — ${err.message}</li>`;
    }
  });
})();
