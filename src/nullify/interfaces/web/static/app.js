/* Nullify web console — vanilla JS, no build step */
"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

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
probeHealth();
setInterval(probeHealth, 15000);

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
  $("intro").hidden = true;
  $("result").hidden = true;
  $("error").hidden = true;

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
    // small floor so the spinner never flashes imperceptibly
    const elapsed = performance.now() - t0;
    if (elapsed < 350) await new Promise((res) => setTimeout(res, 350 - elapsed));
    render(data);
  } catch (err) {
    const box = $("error");
    box.textContent = "Scan failed: " + (err && err.message ? err.message : err);
    box.hidden = false;
  } finally {
    setLoading(false);
  }
});

function setLoading(on) {
  btn.disabled = on;
  spinner.hidden = !on;
  btnLabel.textContent = on ? "Scanning" : "Scan";
  input.disabled = on;
}

/* ---------- rendering ---------- */
const VERDICT_COLORS = { malicious: "#f87171", suspicious: "#fbbf24", benign: "#34d399" };
const R = 36;                       // gauge radius
const CIRC = 2 * Math.PI * R;       // gauge circumference

function render(d) {
  /* verdict card */
  const v = (d.verdict || "unknown").toLowerCase();
  const card = $("verdict-card");
  card.className = "verdict " + (VERDICT_COLORS[v] ? v : "");
  $("verdict-word").textContent = v === "unknown" ? "Unknown" : v;
  $("verdict-type").textContent = d.malware_type && d.malware_type !== v ? d.malware_type : "";

  const conf = Math.max(0, Math.min(1, Number(d.confidence) || 0));
  const pct = Math.round(conf * 100);
  const arc = $("gauge-arc");
  arc.style.strokeDasharray = String(CIRC);
  requestAnimationFrame(() => {
    arc.style.strokeDashoffset = String(CIRC * (1 - conf));
  });
  // count-up animation
  const num = $("confidence");
  animateCount(num, pct);

  /* meta chips */
  const chips = [];
  const t = d.target || {};
  const name = t.path ? String(t.path).replace(/[\\/]+$/, "").split(/[\\/]/).pop() : "—";
  chips.push(chip("file", name, true));
  if (t.size_bytes != null) chips.push(chip("size", fmtBytes(t.size_bytes)));
  if (t.hashes && t.hashes.sha256) chips.push(copyChip("sha256", t.hashes.sha256));
  chips.push(chip("mode", d.mode || "static"));
  chips.push(chip("time", (Number(d.duration_s) || 0).toFixed(2) + "s"));
  if (Array.isArray(d.mitre_ids) && d.mitre_ids.length) {
    chips.push(chip("ATT&CK", d.mitre_ids.join(", ")));
  }
  $("meta-row").innerHTML = chips.join("");
  bindCopyChips();

  /* agents — numbered stage chips */
  $("agents").innerHTML = (d.agents || []).map((a, i) => {
    const st = esc((a.status || "unknown").toLowerCase());
    const nFind = (a.findings || []).length;
    return `<div class="agent">
      <span class="stage-no">0${i + 1}</span>
      <div class="agent-top">
        <span class="agent-name">${esc(a.agent)}</span>
        <span class="agent-ms">${Number(a.duration_s || 0).toFixed(2)}s</span>
      </div>
      <span class="agent-status ${st === "ok" ? "completed" : st}">${st}</span>
      <span class="agent-detail">${nFind ? nFind + " finding" + (nFind > 1 ? "s" : "") : ""}</span>
    </div>`;
  }).join("");

  /* findings */
  const all = (d.agents || []).flatMap((a) => (a.findings || []).map((f) => ({ ...f, agent: a.agent })));
  const box = $("findings");
  $("finding-count").textContent = all.length ? String(all.length) : "";
  if (!all.length) {
    box.innerHTML = `<p class="none">No findings.</p>`;
  } else {
    box.innerHTML = all.map((f) => {
      const sev = esc((f.severity || "info").toLowerCase());
      const tags = [
        `<span class="badge sev sev-${sev}">${sev}</span>`,
        ...(f.mitre_ids || []).map((m) => `<span class="badge mitre">${esc(m)}</span>`),
        `<span class="badge src">${esc(f.agent)}</span>`,
      ].join("");
      const detail = f.detail ? `<div class="finding-detail">${esc(f.detail)}</div>` : "";
      return `<div class="finding sev-${sev}">
        <div class="finding-body">
          <div class="finding-title">${esc(f.title)}</div>
          ${detail}
          <div class="finding-tags">${tags}</div>
        </div>
      </div>`;
    }).join("");
  }

  /* explanation + raw */
  $("explanation").textContent = d.explanation || "—";
  $("raw-json").textContent = JSON.stringify(d, null, 2);

  $("result").hidden = false;
}

function chip(label, value, strong) {
  return `<span class="chip">${esc(label)} <b>${esc(value)}</b></span>`;
}

function copyChip(label, value) {
  return `<span class="chip copyable" data-copy="${esc(value)}" title="Click to copy full hash">${esc(label)} <b>${esc(String(value).slice(0, 16))}…</b></span>`;
}

function bindCopyChips() {
  document.querySelectorAll(".chip.copyable").forEach((el) => {
    el.addEventListener("click", () => {
      navigator.clipboard.writeText(el.dataset.copy).then(() => toast("Copied to clipboard"));
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
  const from = 0;
  function tick(t) {
    const p = Math.min(1, (t - t0) / dur);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = String(Math.round(from + (target - from) * eased));
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function fmtBytes(n) {
  n = Number(n) || 0;
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return (i === 0 ? n : n.toFixed(1)) + " " + units[i];
}

/* ---------- deep link: /?path=/some/file auto-scans ---------- */
const initial = new URLSearchParams(location.search).get("path");
if (initial) {
  input.value = initial;
  form.requestSubmit();
} else {
  input.focus();
}
