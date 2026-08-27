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
        "載入產品 → 「工業級 CNC 切削液」",
        "掃描 187 國資料庫… 12,483 位潛在買主命中",
        "AI 撰寫個人化信件… 3 語版本通過品質門檻",
        "寄送序列啟動 ▸ 2,000 封/日 · 自動跟催",
        "Stefan K.(慕尼黑)接受了會議邀請 — 週四 15:00",
      ],
      ok: "✔ 成約交付 — 會議已排入行事曆",
    },
    {
      lines: [
        "載入產品 → 「運動襪 OEM 代工」",
        "掃描全球採購訊號… 4,209 位潛在買主命中",
        "AI 撰寫個人化信件… 5 語版本通過品質門檻",
        "寄送序列啟動 ▸ 900 封/日 · 自動跟催",
        "Emily C.(底特律)接受了會議邀請 — 週二 10:30",
      ],
      ok: "✔ 成約交付 — 會議已排入行事曆",
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
  const bookings = [
    "✔ 斯圖加特 · 精密機械商 H. Bergmann — 10/28 09:00",
    "✔ 大阪 · 化學品通路 田中物產 — 10/28 14:00",
    "✔ 芝加哥 · 汽車售服集團 Apex — 10/29 10:30",
    "✔ 聖保羅 · 建材進口商 NovaCorp — 10/29 16:00",
    "✔ 新加坡 · 半導體設備商 Straits — 10/30 11:00",
    "✔ 迪拜 · 能源採購商 Gulf Petro — 10/30 13:00",
    "✔ 慕尼黑 · 工具機代理 Krüger Shop — 10/31 15:00",
    "✔ 阿姆斯特丹 · 物流平台 Portflow — 11/01 09:30",
  ];
  const track = document.getElementById("tickerTrack");
  if (track) {
    const items = bookings.map((b) => `<span>${b}</span>`).join("");
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
