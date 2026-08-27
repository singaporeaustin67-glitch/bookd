/* BOOKD — interactions: terminal sim, ticker, reveals, demo pipeline, counters */

(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── hero terminal simulation ─────────────────────────── */
  const log = document.getElementById("terminalLog");
  const result = document.getElementById("terminalResult");

  const CYCLES = [
    {
      lines: [
        'Product loaded → "industrial CNC cutting fluid"',
        "Scanning 187-country pool … 12,483 buyers matched",
        "AI drafts personalized emails … 3 locales pass quality gate",
        "Sequence live ▸ 2,000/day · auto follow-up",
        "Sourcing Director (Munich) accepted — Thu 15:00 CET",
      ],
      ok: "✔ Delivered — meeting on your calendar",
    },
    {
      lines: [
        'Product loaded → "athletic socks, OEM program"',
        "Scanning global buying signals … 4,209 buyers matched",
        "AI drafts personalized emails … 5 locales pass quality gate",
        "Sequence live ▸ 900/day · auto follow-up",
        "VP Procurement (Detroit) accepted — Tue 10:30 EST",
      ],
      ok: "✔ Delivered — meeting on your calendar",
    },
  ];

  let cycleIdx = 0;
  function runTerminal() {
    const cycle = CYCLES[cycleIdx % CYCLES.length];
    cycleIdx += 1;
    log.innerHTML = "";
    result.hidden = true;
    cycle.lines.forEach((line, i) => {
      setTimeout(() => {
        const li = document.createElement("li");
        if (i === cycle.lines.length - 1) li.classList.add("ok");
        li.textContent = line;
        log.appendChild(li);
        if (i === cycle.lines.length - 1) {
          setTimeout(() => {
            result.textContent = cycle.ok;
            result.hidden = false;
          }, 450);
        }
      }, i * (reduceMotion ? 10 : 640));
    });
    const wait = cycle.lines.length * (reduceMotion ? 10 : 640) + 3200;
    setTimeout(runTerminal, wait);
  }
  if (log) runTerminal();

  /* ── ticker feed ──────────────────────────────────────── */
  const lines = [
    "✔ RESULT, NOT DATA",
    "✔ YOU PAY FOR MEETED MEETINGS",
    "✔ NO-SHOW = NO CHARGE",
    "✔ 500M+ CONTACTS — ZERO LEAVE THE VAULT",
    "✔ 40+ LANGUAGES IN THE WRITER",
    "✔ QUALITY GATE BEFORE EVERY SEND",
    "✔ MEETINGS. THAT'S THE DELIVERABLE.",
  ];
  const track = document.getElementById("tickerTrack");
  if (track) {
    const items = lines.map((t) => `<span>${t}</span>`).join("");
    track.innerHTML = items + items; // duplicate for seamless loop
  }

  /* ── scroll reveals ───────────────────────────────────── */
  const reveals = document.querySelectorAll(".reveal");
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
  reveals.forEach((el) => io.observe(el));

  /* ── count-up stats ───────────────────────────────────── */
  const counters = document.querySelectorAll("[data-count]");
  const counterIO = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const target = Number(el.dataset.count);
        const suffix = el.dataset.suffix || "";
        counterIO.unobserve(el);
        if (reduceMotion) {
          el.textContent = `${target}${suffix}`;
          return;
        }
        const start = performance.now();
        const dur = 1400;
        function tick(now) {
          const p = Math.min((now - start) / dur, 1);
          const eased = 1 - Math.pow(1 - p, 3);
          el.textContent = `${Math.round(target * eased)}${suffix}`;
          if (p < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
      });
    },
    { threshold: 0.6 }
  );
  counters.forEach((c) => counterIO.observe(c));

  /* ── hero form → demo section ─────────────────────────── */
  const heroForm = document.getElementById("heroForm");
  const heroInput = document.getElementById("heroInput");
  const demoInput = document.getElementById("demoInput");
  heroForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    if (heroInput.value.trim()) demoInput.value = heroInput.value.trim();
    document.getElementById("demo").scrollIntoView({ behavior: "smooth" });
  });

  /* ── demo pipeline widget ─────────────────────────────── */
  const demoForm = document.getElementById("demoForm");
  const stepsBox = document.getElementById("demoSteps");
  const resultsBox = document.getElementById("demoResults");
  const STEP_TIME = reduceMotion ? 30 : 900;

  demoForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    const steps = stepsBox.querySelectorAll("li");
    resultsBox.hidden = true;
    steps.forEach((s) => s.classList.remove("done", "active"));

    steps.forEach((step, i) => {
      setTimeout(() => {
        steps.forEach((s, j) => {
          if (j < i) s.classList.replace("active", "done");
        });
        step.classList.add("active");
        if (i === steps.length - 1) {
          setTimeout(() => {
            step.classList.replace("active", "done");
            resultsBox.hidden = false;
          }, STEP_TIME);
        }
      }, i * STEP_TIME);
    });
  });
})();
