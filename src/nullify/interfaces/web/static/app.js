/* nullify web console — vanilla js, no build step */
"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

/* ---------- ascii background canvas ---------- */
function startBackground() {
  const canvas = $("bg");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const glyphs = "+.:·≡░▒".split("");
  let cols, rows, cell, field, anim;

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    cell = 18;
    cols = Math.ceil(canvas.width / cell);
    rows = Math.ceil(canvas.height / cell);
    field = new Array(cols * rows);
    for (let i = 0; i < field.length; i++) {
      // sparse blob-ish density using layered value noise
      const x = i % cols, y = (i / cols) | 0;
      const n =
        0.5 + 0.5 * Math.sin(x * 0.11 + Math.cos(y * 0.07) * 2.0) *
        Math.cos(y * 0.09 + Math.sin(x * 0.05) * 1.7);
      field[i] = n > 0.62 ? glyphs[(x * 7 + y * 13) % glyphs.length] : "";
    }
  }

  function draw(t) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = "13px 'Geist Mono', monospace";
    for (let i = 0; i < field.length; i++) {
      const g = field[i];
      if (!g) continue;
      const x = (i % cols) * cell;
      const y = ((i / cols) | 0) * cell;
      const flicker = 0.75 + 0.25 * Math.sin(t * 0.0011 + i * 0.7);
      const alpha = 0.05 + 0.11 * flicker;
      ctx.fillStyle = `rgba(134, 239, 172, ${alpha.toFixed(3)})`;
      ctx.fillText(g, x, y);
    }
    anim = requestAnimationFrame(draw);
  }

  resize();
  window.addEventListener("resize", resize);
  anim = requestAnimationFrame(draw);
  // stop the loop when the tab is hidden — be a good citizen
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) cancelAnimationFrame(anim);
    else anim = requestAnimationFrame(draw);
  });
}

/* ---------- health probe ---------- */
async function probeHealth() {
  const el = $("health");
  try {
    const r = await fetch("/api/health", { cache: "no-store" });
    el.classList.toggle("on", r.ok);
    el.classList.toggle("off", !r.ok);
    el.innerHTML = "<i></i>" + (r.ok ? "engine online" : "engine error");
  } catch {
    el.classList.remove("on");
    el.classList.add("off");
    el.innerHTML = "<i></i>offline";
  }
}

/* ---------- scan ---------- */
const form = $("scan-form");
const input = $("path");
const btn = $("scan-btn");
const btnLabel = btn.querySelector(".btn-label");
const spinner = btn.querySelector(".btn-spinner");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const path = input.value.trim();
  if (!path) {
    input.focus();
    return;
  }
  setLoading(true);

  const t0 = performance.now();
  try {
    const r = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    const data = await r.json().catch(() => null);
    if (!r.ok) {
      throw new Error((data && (data.detail || data.error)) || `HTTP ${r.status}`);
    }
    const elapsed = performance.now() - t0;
    if (elapsed < 350) await new Promise((res) => setTimeout(res, 350 - elapsed));
    render(data);
  } catch (err) {
    const box = $("error");
    box.textContent = "scan failed: " + (err && err.message ? err.message : err);
    box.hidden = false;
    $("result").hidden = true;
  } finally {
    setLoading(false);
  }
});

function setLoading(on) {
  btn.disabled = on;
  spinner.hidden = !on;
  btnLabel.textContent = on ? "scanning" : "scan →";
  input.disabled = on;
  if (on) {
    $("intro").hidden = true;
    $("error").hidden = true;
    $("result").hidden = false;
    $("verdict-card").hidden = true;
    $("meta-row").hidden = true;
    if ($("findings") && $("findings").parentElement) $("findings").parentElement.hidden = true;
    if ($("explanation") && $("explanation").parentElement) $("explanation").parentElement.hidden = true;
    if ($("raw-json") && $("raw-json").parentElement) $("raw-json").parentElement.hidden = true;
    if ($("raw-sec")) $("raw-sec").hidden = true;
    if ($("agents") && $("agents").parentElement) $("agents").parentElement.hidden = false;
    
    $("agents").innerHTML = Array.from({length: 4}).map((_, i) => `
      <div class="skeleton-row" style="opacity: ${1 - i * 0.15}">
        <div class="skeleton" style="width: ${Math.random() * 40 + 40}%"></div>
        <div class="skeleton" style="width: ${Math.random() * 40 + 20}%"></div>
        <div class="skeleton" style="width: ${Math.random() * 40 + 40}%"></div>
        <div class="skeleton" style="width: 100%"></div>
      </div>
    `).join("");
  }
}

/* ---------- rendering ---------- */
function render(d) {
  /* restore visibility */
  $("verdict-card").hidden = false;
  $("meta-row").hidden = false;
  if ($("findings") && $("findings").parentElement) $("findings").parentElement.hidden = false;
  if ($("explanation") && $("explanation").parentElement) $("explanation").parentElement.hidden = false;
  if ($("raw-json") && $("raw-json").parentElement) $("raw-json").parentElement.hidden = false;
  if ($("raw-sec")) $("raw-sec").hidden = false;

  /* verdict */
  const v = (d.verdict || "unknown").toLowerCase();
  const card = $("verdict-card");
  card.className = "verdict " + (["malicious", "suspicious", "benign"].includes(v) ? v : "");
  $("verdict-word").textContent = v === "unknown" ? "unknown" : v;
  $("verdict-type").textContent = d.malware_type && d.malware_type !== v ? d.malware_type : "";

  const conf = Math.max(0, Math.min(1, Number(d.confidence) || 0));
  const pct = Math.round(conf * 100);
  renderConfBar(pct);
  animateCount($("confidence"), pct);

  /* meta chips */
  const chips = [];
  const t = d.target || {};
  const name = t.path ? String(t.path).replace(/[\\/]+$/, "").split(/[\\/]/).pop() : "—";
  chips.push(chip("file", name));
  if (t.size_bytes != null) chips.push(chip("size", fmtBytes(t.size_bytes)));
  if (t.hashes && t.hashes.sha256) chips.push(copyChip("sha256", t.hashes.sha256));
  chips.push(chip("mode", d.mode || "static"));
  chips.push(chip("time", (Number(d.duration_s) || 0).toFixed(2) + "s"));
  if (Array.isArray(d.mitre_ids) && d.mitre_ids.length) {
    chips.push(chip("attack", d.mitre_ids.join(", ")));
  }
  $("meta-row").innerHTML = chips.join("");
  bindCopyChips();

  /* pipeline — d1rshan-style rows: name … status · time · findings */
  $("agents").innerHTML = (d.agents || []).map((a, i) => {
    const st = (a.status || "unknown").toLowerCase();
    const nFind = (a.findings || []).length;
    const isSkipped = st === "skipped";
    const detail = nFind ? `${nFind} finding${nFind > 1 ? "s" : ""}` : (isSkipped && a.error ? a.error : "");
    const titleAttr = isSkipped && a.error ? ` title="${esc(a.error)}"` : "";
    return `<div class="agent" style="animation-delay: ${i * 0.05}s">
      <span class="r-name"${titleAttr}>${esc(a.agent.replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase())}</span>
      <span class="r-desc"${titleAttr}>${esc(detail || "—")}</span>
      <span class="r-tag agent-status ${st === "ok" ? "" : esc(st)}"${titleAttr}>${esc(st)}</span>
      <span class="r-tag">${Number(a.duration_s || 0).toFixed(2)}s</span>
    </div>`;
  }).join("");

  /* findings */
  const all = (d.agents || []).flatMap((a) => (a.findings || []).map((f) => ({ ...f, agent: a.agent })));
  $("finding-count").textContent = all.length ? `(${all.length})` : "";
  $("findings").innerHTML = all.length
    ? all.map((f, i) => {
        const sev = esc((f.severity || "info").toLowerCase());
        const tags = [
          `<span class="badge sev-${sev}">${sev}</span>`,
          ...(f.mitre_ids || []).map((m) => `<span class="badge mitre">${esc(m)}</span>`),
          `<span class="badge">${esc(f.agent)}</span>`,
        ].join("");
        const detail = f.detail ? `<div class="finding-detail">${esc(f.detail)}</div>` : "";
        return `<div class="finding sev-${sev}" style="animation-delay: ${i * 0.05}s">
          <div class="f-top">
            <span class="r-name">${esc(f.title)}</span>
            ${tags}
          </div>
          ${detail}
        </div>`;
      }).join("")
    : `<p class="r-desc">no findings.</p>`;

  /* why + raw */
  $("explanation").textContent = d.explanation || "—";
  $("raw-json").textContent = JSON.stringify(d, null, 2);

  $("result").hidden = false;
}

/* ascii confidence bar — block characters, d1rshan green (25 cells = 4% steps) */
function renderConfBar(pct) {
  const width = 25;
  const filled = Math.round((pct / 100) * width);
  const full = "█".repeat(filled);
  const empty = "░".repeat(width - filled);
  $("conf-bar").textContent = `${full}${empty}`;
}

function chip(label, value) {
  return `<span class="chip">${esc(label)} <b>${esc(value)}</b></span>`;
}

function copyChip(label, value) {
  return `<span class="chip copyable" data-copy="${esc(value)}" title="click to copy full hash">${esc(label)} <b>${esc(String(value).slice(0, 16))}…</b></span>`;
}

function bindCopyChips() {
  document.querySelectorAll(".chip.copyable").forEach((el) => {
    el.addEventListener("click", () => {
      navigator.clipboard.writeText(el.dataset.copy).then(() => toast("copied to clipboard"));
    });
  });
}

let toastTimer = null;
function toast(msg) {
  let el = $("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 1600);
}

function animateCount(el, target) {
  const t0 = performance.now();
  const dur = 700;
  function tick(t) {
    const p = Math.min(1, (t - t0) / dur);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = String(Math.round(target * eased));
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function fmtBytes(n) {
  n = Number(n) || 0;
  const units = ["b", "kb", "mb", "gb"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return (i === 0 ? n : n.toFixed(1)) + " " + units[i];
}

/* ---------- raw report toggle ---------- */
$("raw-toggle").addEventListener("click", () => {
  const raw = $("raw-json");
  raw.hidden = !raw.hidden;
  $("raw-toggle").textContent = raw.hidden ? "view raw report →" : "hide raw report →";
  if ($("raw-copy")) $("raw-copy").hidden = raw.hidden;
});

if ($("raw-copy")) {
  $("raw-copy").addEventListener("click", () => {
    navigator.clipboard.writeText($("raw-json").textContent).then(() => toast("copied raw report"));
  });
}

/* ---------- boot ---------- */
startBackground();
probeHealth();
setInterval(probeHealth, 15000);

/* deep link: /?path=/some/file auto-scans */
const initial = new URLSearchParams(location.search).get("path");
if (initial) {
  input.value = initial;
  form.requestSubmit();
} else {
  input.focus();
}

/* ---------- keybindings ---------- */
document.addEventListener("keydown", (e) => {
  if (e.key === "/" && document.activeElement !== input) {
    e.preventDefault();
    input.focus();
  } else if (e.key === "Escape" && document.activeElement === input) {
    input.value = "";
    input.blur();
  }
});
