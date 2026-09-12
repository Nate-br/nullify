/* nullify web console — Framer AI Agent Design System
   Vanilla JS · Zero Build Step · Real-time Reactive Dashboard */
"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// Global State
let currentReport = null;
let currentFilter = "all";
let scanMode = "static";
let sampleCatalog = {};

/* ---------- Health Probe ---------- */
async function probeHealth() {
  const el = $("health");
  const textEl = $("health-text");
  try {
    const r = await fetch("/api/health", { cache: "no-store" });
    const ok = r.ok;
    el.classList.toggle("on", ok);
    el.classList.toggle("off", !ok);
    textEl.textContent = ok ? "Engine Ready" : "Engine Error";
  } catch {
    el.classList.remove("on");
    el.classList.add("off");
    textEl.textContent = "Offline";
  }
}

/* ---------- Samples Catalog ---------- */
async function loadSamplesCatalog() {
  try {
    const r = await fetch("/api/samples");
    if (r.ok) {
      const data = await r.json();
      (data.samples || []).forEach((s) => {
        sampleCatalog[s.id] = s;
      });
    }
  } catch (err) {
    console.debug("Could not load samples catalog:", err);
  }
}

/* ---------- Mode Selector ---------- */
const btnStatic = $("mode-static");
const btnDeep = $("mode-deep");

if (btnStatic && btnDeep) {
  btnStatic.addEventListener("click", () => {
    scanMode = "static";
    btnStatic.classList.add("active");
    btnDeep.classList.remove("active");
  });

  btnDeep.addEventListener("click", () => {
    scanMode = "deep";
    btnDeep.classList.add("active");
    btnStatic.classList.remove("active");
  });
}

/* ---------- Form, Input & Buttons ---------- */
const form = $("scan-form");
const input = $("path");
const btn = $("scan-btn");
const btnLabel = btn.querySelector(".btn-label");
const spinner = btn.querySelector(".btn-spinner");
const fileTrigger = $("file-trigger");
const fileInput = $("file-input");
const dropZone = $("drop-zone");

function setLoading(on) {
  btn.disabled = on;
  spinner.hidden = !on;
  btnLabel.textContent = on ? "Analyzing…" : "Run Agent →";
  input.disabled = on;

  if (on) {
    $("intro").hidden = true;
    $("error").hidden = true;
    $("result").hidden = false;

    // Show skeletons for agents while scanning
    const agentsEl = $("agents");
    if (agentsEl) {
      agentsEl.innerHTML = Array.from({ length: 6 }).map((_, i) => `
        <div class="agent-node" style="opacity: 0.5;">
          <div class="agent-node-top">
            <span class="agent-idx">0${i + 1}</span>
            <span class="agent-status-badge">Running…</span>
          </div>
          <span class="agent-name">Agent ${i + 1}</span>
          <span class="agent-metric">Processing evidence…</span>
        </div>
      `).join("");
    }
  }
}

/* ---------- Execute Scan via API ---------- */
async function executeScan(path, mode = scanMode) {
  setLoading(true);
  const t0 = performance.now();
  try {
    const r = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, mode }),
    });
    const data = await r.json().catch(() => null);
    if (!r.ok) {
      throw new Error((data && (data.detail || data.error)) || `HTTP ${r.status}`);
    }
    const elapsed = performance.now() - t0;
    if (elapsed < 350) await new Promise((res) => setTimeout(res, 350 - elapsed));
    currentReport = data;
    render(data);
  } catch (err) {
    const box = $("error");
    box.textContent = "Scan failed: " + (err && err.message ? err.message : err);
    box.hidden = false;
    $("result").hidden = true;
    $("intro").hidden = false;
  } finally {
    setLoading(false);
  }
}

/* ---------- Execute Upload via API ---------- */
async function executeUpload(file, mode = scanMode) {
  setLoading(true);
  const t0 = performance.now();
  try {
    const formData = new FormData();
    formData.append("file", file);

    const r = await fetch(`/api/upload?mode=${encodeURIComponent(mode)}`, {
      method: "POST",
      body: formData,
    });
    const data = await r.json().catch(() => null);
    if (!r.ok) {
      throw new Error((data && (data.detail || data.error)) || `HTTP ${r.status}`);
    }
    input.value = file.name;
    const elapsed = performance.now() - t0;
    if (elapsed < 350) await new Promise((res) => setTimeout(res, 350 - elapsed));
    currentReport = data;
    render(data);
  } catch (err) {
    const box = $("error");
    box.textContent = "Upload scan failed: " + (err && err.message ? err.message : err);
    box.hidden = false;
    $("result").hidden = true;
    $("intro").hidden = false;
  } finally {
    setLoading(false);
  }
}

/* Form submission */
form.addEventListener("submit", (e) => {
  e.preventDefault();
  const path = input.value.trim();
  if (!path) {
    input.focus();
    return;
  }
  executeScan(path, scanMode);
});

/* File picker trigger */
if (fileTrigger && fileInput) {
  fileTrigger.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      executeUpload(e.target.files[0], scanMode);
    }
  });
}

/* Drag and Drop handling */
if (dropZone) {
  dropZone.addEventListener("click", () => fileInput && fileInput.click());

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove("dragover");
    });
  });

  dropZone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files[0]) {
      executeUpload(dt.files[0], scanMode);
    }
  });
}

/* Quick synthetic demo chips */
document.querySelectorAll(".sample-chip").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const sampleId = btn.dataset.sample;
    if (sampleCatalog[sampleId]) {
      const sample = sampleCatalog[sampleId];
      input.value = sample.path;
      executeScan(sample.path, scanMode);
    } else {
      // Re-fetch catalog if needed
      await loadSamplesCatalog();
      if (sampleCatalog[sampleId]) {
        input.value = sampleCatalog[sampleId].path;
        executeScan(sampleCatalog[sampleId].path, scanMode);
      }
    }
  });
});

/* ---------- Render Scan Report ---------- */
function render(d) {
  currentReport = d;

  /* 1. Verdict Card */
  const v = (d.verdict || "unknown").toLowerCase();
  const card = $("verdict-card");
  card.className = "bento-card bento-verdict " + (["malicious", "suspicious", "benign"].includes(v) ? v : "unknown");
  $("verdict-word").textContent = v;
  
  const typePill = $("verdict-type");
  const malType = d.malware_type && d.malware_type !== v ? d.malware_type : "";
  typePill.textContent = malType ? `Type: ${malType}` : (v === "benign" ? "Clean" : "");
  typePill.hidden = !typePill.textContent;

  /* 2. SVG Radial Confidence Meter */
  const conf = Math.max(0, Math.min(1, Number(d.confidence) || 0));
  const pct = Math.round(conf * 100);
  renderRadialGauge(pct, v);

  /* 3. Metadata Chips */
  const chips = [];
  const t = d.target || {};
  const name = t.path ? String(t.path).replace(/[\\/]+$/, "").split(/[\\/]/).pop() : "—";
  chips.push(chip("Target", name));
  if (t.size_bytes != null) chips.push(chip("Size", fmtBytes(t.size_bytes)));
  if (t.hashes && t.hashes.sha256) chips.push(copyChip("SHA-256", t.hashes.sha256));
  chips.push(chip("Mode", d.mode || "static"));
  chips.push(chip("Scan Time", (Number(d.duration_s) || 0).toFixed(2) + "s"));
  $("meta-row").innerHTML = chips.join("");
  bindCopyChips();

  /* 4. AI Reasoning Rationale */
  $("explanation").textContent = d.explanation || "No rationale generated.";

  /* 5. 6-Agent Pipeline Flow */
  const stages = [
    { name: "Triage", desc: "Magic bytes & entropy" },
    { name: "Static", desc: "Imports, capa & YARA" },
    { name: "Dynamic", desc: "CAPEv2 detonation" },
    { name: "LogCorrelation", desc: "Sysmon & event logs" },
    { name: "Classifier", desc: "XGBoost EMBER ML" },
    { name: "Reasoning", desc: "Verdict synthesis" },
  ];

  const agentResults = d.agents || [];
  $("agents").innerHTML = stages.map((s, idx) => {
    const found = agentResults.find((a) => a.agent.toLowerCase() === s.name.toLowerCase());
    const status = found ? (found.status || "completed").toLowerCase() : "skipped";
    const duration = found ? (Number(found.duration_s || 0).toFixed(2) + "s") : "—";
    const nFind = found && found.findings ? found.findings.length : 0;
    const findText = nFind ? `${nFind} finding${nFind > 1 ? "s" : ""}` : s.desc;

    return `
      <div class="agent-node">
        <div class="agent-node-top">
          <span class="agent-idx">0${idx + 1}</span>
          <span class="agent-status-badge ${esc(status)}">${esc(status)}</span>
        </div>
        <span class="agent-name">${esc(s.name)}</span>
        <div class="agent-metric">
          <span>${esc(findText)}</span>
          <b>${esc(duration)}</b>
        </div>
      </div>
    `;
  }).join("");

  /* 6. MITRE ATT&CK Matrix */
  const mitreIds = Array.isArray(d.mitre_ids) ? d.mitre_ids : [];
  $("mitre-count").textContent = `${mitreIds.length} mapped`;
  const mitreListEl = $("mitre-list");
  if (mitreIds.length) {
    mitreListEl.innerHTML = mitreIds.map((tid) => {
      const cleanTid = tid.replace(/[^A-Za-z0-9.]/g, "");
      return `
        <a href="https://attack.mitre.org/techniques/${esc(cleanTid.replace(".", "/"))}/" target="_blank" rel="noopener" class="mitre-pill" title="View on MITRE ATT&CK">
          <span>⚡</span> <b>${esc(tid)}</b>
        </a>
      `;
    }).join("");
  } else {
    mitreListEl.innerHTML = `<span style="font-size: 13px; color: var(--text-muted);">No MITRE ATT&CK techniques observed for this sample.</span>`;
  }

  /* 7. Findings Deep Dive with Filter */
  currentFilter = "all";
  updateFilterButtons();
  renderFindings();

  /* 8. YARA Preview Reset */
  $("yara-rule-preview").textContent = "// Click below to derive a YARA rule from this sample's findings";
  $("btn-copy-yara").hidden = true;

  /* 9. Raw JSON */
  $("raw-json").textContent = JSON.stringify(d, null, 2);

  $("result").hidden = false;
  $("intro").hidden = true;
}

/* ---------- Radial Gauge Meter ---------- */
function renderRadialGauge(pct, verdict) {
  const circle = $("gauge-circle");
  const number = $("confidence");
  if (!circle || !number) return;

  const circumference = 2 * Math.PI * 60; // radius = 60, ~377
  circle.style.strokeDasharray = circumference;
  const offset = circumference - (pct / 100) * circumference;
  circle.style.strokeDashoffset = offset;

  // Set stroke color based on verdict
  if (verdict === "malicious") {
    circle.style.stroke = "var(--malicious)";
  } else if (verdict === "suspicious") {
    circle.style.stroke = "var(--suspicious)";
  } else {
    circle.style.stroke = "var(--benign)";
  }

  // Animate counter
  animateCounter(number, pct);
}

function animateCounter(el, target) {
  const t0 = performance.now();
  const dur = 600;
  function tick(t) {
    const p = Math.min(1, (t - t0) / dur);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = `${Math.round(target * eased)}%`;
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

/* ---------- Metadata Chip Helpers ---------- */
function chip(label, value) {
  return `<span class="meta-chip">${esc(label)}: <b>${esc(value)}</b></span>`;
}

function copyChip(label, value) {
  const truncated = String(value).length > 16 ? String(value).slice(0, 16) + "…" : value;
  return `<span class="meta-chip copyable" data-copy="${esc(value)}" title="Click to copy full value">${esc(label)}: <b>${esc(truncated)}</b> 📋</span>`;
}

function bindCopyChips() {
  document.querySelectorAll(".meta-chip.copyable").forEach((el) => {
    el.addEventListener("click", () => {
      navigator.clipboard.writeText(el.dataset.copy).then(() => toast("Copied to clipboard"));
    });
  });
}

/* ---------- Findings Filtering & Rendering ---------- */
function renderFindings() {
  if (!currentReport) return;
  const all = (currentReport.agents || []).flatMap((a) =>
    (a.findings || []).map((f) => ({ ...f, agent: a.agent }))
  );

  $("finding-count").textContent = `${all.length} findings`;

  const filtered = currentFilter === "all"
    ? all
    : all.filter((f) => (f.severity || "info").toLowerCase() === currentFilter);

  const container = $("findings");
  if (!filtered.length) {
    container.innerHTML = `<p style="padding: 16px; color: var(--text-muted); font-size: 13.5px;">No findings matching "${currentFilter}".</p>`;
    return;
  }

  container.innerHTML = filtered.map((f) => {
    const sev = esc((f.severity || "info").toLowerCase());
    const detailHtml = f.detail ? `<p class="finding-detail-text">${esc(f.detail)}</p>` : "";
    const mitreTags = (f.mitre_ids || []).map((m) => `<span class="badge-sev low">${esc(m)}</span>`).join(" ");

    return `
      <div class="finding-row">
        <div class="finding-top">
          <div class="finding-title-group">
            <span class="badge-sev ${sev}">${sev}</span>
            <span class="finding-title">${esc(f.title)}</span>
            ${mitreTags}
          </div>
          <span class="finding-agent-tag">${esc(f.agent)}</span>
        </div>
        ${detailHtml}
      </div>
    `;
  }).join("");
}

function updateFilterButtons() {
  document.querySelectorAll(".filter-pill").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.filter === currentFilter);
  });
}

document.querySelectorAll(".filter-pill").forEach((btn) => {
  btn.addEventListener("click", () => {
    currentFilter = btn.dataset.filter;
    updateFilterButtons();
    renderFindings();
  });
});

/* ---------- YARA Rule Synthesis ---------- */
const btnGenYara = $("btn-gen-yara");
const btnCopyYara = $("btn-copy-yara");

if (btnGenYara) {
  btnGenYara.addEventListener("click", async () => {
    if (!currentReport) return;
    btnGenYara.disabled = true;
    btnGenYara.textContent = "Synthesizing…";

    try {
      const findings = (currentReport.agents || []).flatMap((a) => a.findings || []);
      const staticAgent = (currentReport.agents || []).find((a) => a.agent === "Static");
      const imports = staticAgent && staticAgent.data ? (staticAgent.data.imports || []) : [];

      const r = await fetch("/api/generate-rule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          findings,
          imports,
          family: currentReport.malware_type || "Malware",
          name_hint: (currentReport.target && currentReport.target.path ? currentReport.target.path.split(/[\\/]/).pop() : "Sample"),
        }),
      });

      const res = await r.json();
      if (res.rule) {
        $("yara-rule-preview").textContent = res.rule;
        btnCopyYara.hidden = false;
      }
    } catch (err) {
      toast("Failed to generate YARA rule: " + err);
    } finally {
      btnGenYara.disabled = false;
      btnGenYara.textContent = "Regenerate Rule";
    }
  });
}

if (btnCopyYara) {
  btnCopyYara.addEventListener("click", () => {
    const text = $("yara-rule-preview").textContent;
    navigator.clipboard.writeText(text).then(() => toast("YARA rule copied to clipboard"));
  });
}

/* ---------- Raw JSON Report Toggle & Copy ---------- */
const rawToggle = $("raw-toggle");
const rawCopy = $("raw-copy");
const rawJson = $("raw-json");

if (rawToggle && rawJson) {
  rawToggle.addEventListener("click", () => {
    rawJson.hidden = !rawJson.hidden;
    rawToggle.textContent = rawJson.hidden ? "View Raw Report" : "Hide Raw Report";
    if (rawCopy) rawCopy.hidden = rawJson.hidden;
  });
}

if (rawCopy && rawJson) {
  rawCopy.addEventListener("click", () => {
    navigator.clipboard.writeText(rawJson.textContent).then(() => toast("Raw JSON copied to clipboard"));
  });
}

/* ---------- Toast System ---------- */
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
  toastTimer = setTimeout(() => el.classList.remove("show"), 2000);
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

/* ---------- Keybindings ---------- */
document.addEventListener("keydown", (e) => {
  if (e.key === "/" && document.activeElement !== input) {
    e.preventDefault();
    input.focus();
    input.select();
  } else if (e.key === "Escape" && document.activeElement === input) {
    input.value = "";
    input.blur();
  }
});

/* ---------- Init & Boot ---------- */
probeHealth();
setInterval(probeHealth, 15000);
loadSamplesCatalog();

// Auto-scan if deep link has ?path=...
const initial = new URLSearchParams(location.search).get("path");
if (initial && initial !== "/dev/null") {
  input.value = initial;
  executeScan(initial, scanMode);
} else {
  input.focus();
}
