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

/* ---------- Navbar Active Spy & Smooth Navigation ---------- */
function initNavigation() {
  const brandLink = $("nav-brand-logo");
  const navLinks = Array.from(document.querySelectorAll("#nav-menu-links .nav-item[data-section]"));
  const sectionIds = ["canvas", "intelligence", "pipeline", "manifesto"];
  const sections = sectionIds
    .map((id) => document.getElementById(id))
    .filter(Boolean);

  function setActive(activeId) {
    navLinks.forEach((link) => {
      const match = link.getAttribute("data-section") === activeId;
      link.classList.toggle("active", match);
    });
  }

  // Smooth scroll for brand logo (scrolls to top hero, clears active nav items)
  if (brandLink) {
    brandLink.addEventListener("click", (e) => {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: "smooth" });
      if (location.hash) {
        history.pushState(null, "", window.location.pathname);
      }
      setActive(null);
    });
  }

  // Smooth scroll & instant active state on nav item click
  navLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      const targetId = link.getAttribute("data-section");
      const targetEl = document.getElementById(targetId);
      if (targetEl) {
        e.preventDefault();
        targetEl.scrollIntoView({ behavior: "smooth" });
        history.pushState(null, "", `#${targetId}`);
        setActive(targetId);
      }
    });
  });

  // ScrollSpy with IntersectionObserver & scroll fallback
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        if (window.scrollY < 250) {
          setActive(null);
          return;
        }
        const visible = entries.filter((entry) => entry.isIntersecting);
        if (visible.length > 0) {
          visible.sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
          setActive(visible[0].target.id);
        }
      },
      {
        rootMargin: "-25% 0px -55% 0px",
        threshold: [0, 0.25, 0.5],
      }
    );

    sections.forEach((sec) => observer.observe(sec));
  }

  window.addEventListener(
    "scroll",
    () => {
      if (window.scrollY < 250) {
        setActive(null);
      }
    },
    { passive: true }
  );
}

/* ---------- Interactive Pipeline Terminal Simulator ---------- */
function initPipelineTerminal() {
  const terminal = $("interactive-terminal");
  if (!terminal) return;

  const codePane = $("term-code-pane");
  const gutters = $("term-gutters");
  const streamLines = $("term-stream-lines");
  const timingBadge = $("term-timing-badge");
  const runBtn = $("term-run-btn");
  const copyBtn = $("term-copy-btn");
  const tabBtns = terminal.querySelectorAll(".term-tab");
  const targetPills = terminal.querySelectorAll(".term-target-pill");

  let activeTab = "python";
  let activeScenario = "elf";
  let isRunning = false;
  let hasAutoRun = false;

  const scenarios = {
    elf: {
      target: "/opt/bin/sample.elf",
      mode: "static",
      timing: "3.47s duration · offline-first",
      verdictClass: "benign",
      verdictText: "BENIGN",
      verdictDetail: "90% confidence · 3.47s duration · offline-first",
      steps: [
        { tag: "[agent:mesh]", msg: "Autonomous pipeline initialized · 6 cooperating workers online" },
        { tag: "[agent:static]", msg: "ELF header: x86-64 LSB executable · Shannon entropy: 7.912" },
        { tag: "[agent:classifier]", msg: "XGBoost on EMBER evaluated 2,381 features · model confidence: 90.0%" },
        { tag: "[agent:mitre]", msg: "0 ATT&CK techniques detected · Clean telemetry baseline verified" },
      ],
      python: [
        { num: 1, html: '<span class="tok-cm"># initialize nullify autonomous threat pipeline</span>' },
        { num: 2, html: '<span class="tok-kw">import</span> nullify' },
        { num: 3, html: '' },
        { num: 4, html: '<span class="tok-var">analysis</span> <span class="tok-op">=</span> nullify.<span class="tok-fn">scan</span>(target=<span class="tok-str">"/opt/bin/sample.elf"</span>, mode=<span class="tok-str">"static"</span>)' },
        { num: 5, html: '' },
        { num: 6, html: '<span class="tok-cm"># synthesize explainable verdict and MITRE telemetry</span>' },
        { num: 7, html: '<span class="tok-var">verdict</span> <span class="tok-op">=</span> analysis.<span class="tok-var">verdict</span>' },
        { num: 8, html: '<span class="tok-var">reasons</span> <span class="tok-op">=</span> analysis.<span class="tok-var">explanation</span>' },
        { num: 9, html: '' },
        { num: 10, html: '<span class="tok-fn">print</span>(<span class="tok-str">f"→ verdict: {verdict} · {analysis.confidence}% · offline-first"</span>)' },
      ],
      cli: [
        { num: 1, html: '<span class="tok-cm"># execute air-gapped threat inspection in CLI</span>' },
        { num: 2, html: '<span class="tok-op">$</span> nullify scan /opt/bin/sample.elf --mode static' },
        { num: 3, html: '<span class="tok-cm">─────────────────────────────────────────────────────────────────</span>' },
        { num: 4, html: '<span class="tok-var">[agent:triage]</span>     ELF 64-bit LSB executable, x86-64, dynamic' },
        { num: 5, html: '<span class="tok-var">[agent:entropy]</span>    Shannon entropy: 7.912 (non-packed)' },
        { num: 6, html: '<span class="tok-var">[agent:ember]</span>      XGBoost ML model: 90.0% confidence' },
        { num: 7, html: '<span class="tok-var">[agent:mitre]</span>      0 MITRE ATT&CK techniques detected' },
        { num: 8, html: '<span class="tok-cm">─────────────────────────────────────────────────────────────────</span>' },
        { num: 9, html: '<span class="tok-fn">→ verdict:</span> <span class="tok-str">BENIGN · 90% confidence · 3.47s duration · offline-first</span>' },
      ],
      json: [
        { num: 1, html: '{' },
        { num: 2, html: '  <span class="tok-str">"target"</span>: <span class="tok-str">"/opt/bin/sample.elf"</span>,' },
        { num: 3, html: '  <span class="tok-str">"format"</span>: <span class="tok-str">"ELF"</span>,' },
        { num: 4, html: '  <span class="tok-str">"verdict"</span>: <span class="tok-str">"BENIGN"</span>,' },
        { num: 5, html: '  <span class="tok-str">"confidence"</span>: <span class="tok-num">0.90</span>,' },
        { num: 6, html: '  <span class="tok-str">"features_evaluated"</span>: <span class="tok-num">2381</span>,' },
        { num: 7, html: '  <span class="tok-str">"execution_time_ms"</span>: <span class="tok-num">3470</span>,' },
        { num: 8, html: '  <span class="tok-str">"offline_first"</span>: <span class="tok-kw">true</span>' },
        { num: 9, html: '}' },
      ],
    },
    trojan: {
      target: "/var/quarantine/trojan_dropper.exe",
      mode: "deep",
      timing: "5.12s duration · CAPEv2 detonation",
      verdictClass: "malicious",
      verdictText: "MALICIOUS",
      verdictDetail: "99.46% confidence · Trojan.Dropper · Run-key persistence",
      steps: [
        { tag: "[agent:mesh]", msg: "Autonomous pipeline initialized · Detonation sandbox armed" },
        { tag: "[agent:triage]", msg: "PE32+ executable · Section anomaly in .rsrc (Entropy: 7.98)" },
        { tag: "[agent:detonate]", msg: "CAPEv2: WinExec spawn, CreateRemoteThread, Registry Run-key" },
        { tag: "[agent:classifier]", msg: "XGBoost EMBER: 99.46% malware probability · Trojan.Dropper" },
      ],
      python: [
        { num: 1, html: '<span class="tok-cm"># initialize nullify autonomous threat pipeline</span>' },
        { num: 2, html: '<span class="tok-kw">import</span> nullify' },
        { num: 3, html: '' },
        { num: 4, html: '<span class="tok-var">analysis</span> <span class="tok-op">=</span> nullify.<span class="tok-fn">scan</span>(target=<span class="tok-str">"/var/quarantine/trojan_dropper.exe"</span>, mode=<span class="tok-str">"deep"</span>)' },
        { num: 5, html: '' },
        { num: 6, html: '<span class="tok-cm"># synthesize explainable verdict and MITRE telemetry</span>' },
        { num: 7, html: '<span class="tok-var">verdict</span> <span class="tok-op">=</span> analysis.<span class="tok-var">verdict</span>' },
        { num: 8, html: '<span class="tok-var">reasons</span> <span class="tok-op">=</span> analysis.<span class="tok-var">explanation</span>' },
        { num: 9, html: '' },
        { num: 10, html: '<span class="tok-fn">print</span>(<span class="tok-str">f"→ verdict: {verdict} · {analysis.confidence}% · {analysis.family}"</span>)' },
      ],
      cli: [
        { num: 1, html: '<span class="tok-cm"># execute sandboxed detonation inspection in CLI</span>' },
        { num: 2, html: '<span class="tok-op">$</span> nullify scan /var/quarantine/trojan_dropper.exe --mode deep' },
        { num: 3, html: '<span class="tok-cm">─────────────────────────────────────────────────────────────────</span>' },
        { num: 4, html: '<span class="tok-var">[agent:triage]</span>     PE32+ executable, WinExec + CreateRemoteThread' },
        { num: 5, html: '<span class="tok-var">[agent:detonate]</span>   Sandbox spawn verified · HKCU\\Run persistence' },
        { num: 6, html: '<span class="tok-var">[agent:ember]</span>      XGBoost ML model: 99.46% malware probability' },
        { num: 7, html: '<span class="tok-var">[agent:mitre]</span>      T1059 (Command Execution), T1547 (Run-Key)' },
        { num: 8, html: '<span class="tok-cm">─────────────────────────────────────────────────────────────────</span>' },
        { num: 9, html: '<span class="tok-fn">→ verdict:</span> <span class="tok-str">MALICIOUS · 99.46% confidence · Trojan.Dropper</span>' },
      ],
      json: [
        { num: 1, html: '{' },
        { num: 2, html: '  <span class="tok-str">"target"</span>: <span class="tok-str">"/var/quarantine/trojan_dropper.exe"</span>,' },
        { num: 3, html: '  <span class="tok-str">"format"</span>: <span class="tok-str">"PE"</span>,' },
        { num: 4, html: '  <span class="tok-str">"verdict"</span>: <span class="tok-str">"MALICIOUS"</span>,' },
        { num: 5, html: '  <span class="tok-str">"confidence"</span>: <span class="tok-num">0.9946</span>,' },
        { num: 6, html: '  <span class="tok-str">"family"</span>: <span class="tok-str">"Trojan.Dropper"</span>,' },
        { num: 7, html: '  <span class="tok-str">"mitre_attack"</span>: [<span class="tok-str">"T1059"</span>, <span class="tok-str">"T1547"</span>],' },
        { num: 8, html: '  <span class="tok-str">"execution_time_ms"</span>: <span class="tok-num">5120</span>' },
        { num: 9, html: '}' },
      ],
    },
    sysmon: {
      target: "/var/log/sysmon_event.jsonl",
      mode: "static",
      timing: "2.18s duration · Behavioral correlation",
      verdictClass: "suspicious",
      verdictText: "SUSPICIOUS",
      verdictDetail: "88.2% confidence · T1059 Command & Scripting · T1053 Schtasks",
      steps: [
        { tag: "[agent:mesh]", msg: "Autonomous pipeline initialized · Ingesting log event stream" },
        { tag: "[agent:log]", msg: "5 events correlated · Temp path execution cmd.exe /c dropper.exe" },
        { tag: "[agent:mitre]", msg: "T1059.003 Command-Line Interface · T1053 Scheduled Task created" },
        { tag: "[agent:reasoning]", msg: "High-risk chain: Temp process spawn + LSASS memory query" },
      ],
      python: [
        { num: 1, html: '<span class="tok-cm"># initialize nullify autonomous threat pipeline</span>' },
        { num: 2, html: '<span class="tok-kw">import</span> nullify' },
        { num: 3, html: '' },
        { num: 4, html: '<span class="tok-var">analysis</span> <span class="tok-op">=</span> nullify.<span class="tok-fn">scan</span>(target=<span class="tok-str">"/var/log/sysmon_event.jsonl"</span>, mode=<span class="tok-str">"static"</span>)' },
        { num: 5, html: '' },
        { num: 6, html: '<span class="tok-cm"># synthesize explainable verdict and MITRE telemetry</span>' },
        { num: 7, html: '<span class="tok-var">verdict</span> <span class="tok-op">=</span> analysis.<span class="tok-var">verdict</span>' },
        { num: 8, html: '<span class="tok-var">reasons</span> <span class="tok-op">=</span> analysis.<span class="tok-var">explanation</span>' },
        { num: 9, html: '' },
        { num: 10, html: '<span class="tok-fn">print</span>(<span class="tok-str">f"→ verdict: {verdict} · {analysis.confidence}% · MITRE mapped"</span>)' },
      ],
      cli: [
        { num: 1, html: '<span class="tok-cm"># correlate behavioral Sysmon logs in CLI</span>' },
        { num: 2, html: '<span class="tok-op">$</span> nullify scan /var/log/sysmon_event.jsonl' },
        { num: 3, html: '<span class="tok-cm">─────────────────────────────────────────────────────────────────</span>' },
        { num: 4, html: '<span class="tok-var">[agent:log]</span>        5 events parsed · EventID 1 (ProcessCreate)' },
        { num: 5, html: '<span class="tok-var">[agent:behavior]</span>   Temp path execution detected · schtasks /create' },
        { num: 6, html: '<span class="tok-var">[agent:reasoning]</span>  Privilege escalation chain identified' },
        { num: 7, html: '<span class="tok-var">[agent:mitre]</span>      T1059.003, T1053, T1003 mapped' },
        { num: 8, html: '<span class="tok-cm">─────────────────────────────────────────────────────────────────</span>' },
        { num: 9, html: '<span class="tok-fn">→ verdict:</span> <span class="tok-str">SUSPICIOUS · 88.2% confidence · 2.18s duration</span>' },
      ],
      json: [
        { num: 1, html: '{' },
        { num: 2, html: '  <span class="tok-str">"target"</span>: <span class="tok-str">"/var/log/sysmon_event.jsonl"</span>,' },
        { num: 3, html: '  <span class="tok-str">"format"</span>: <span class="tok-str">"JSONL_SYSMON"</span>,' },
        { num: 4, html: '  <span class="tok-str">"verdict"</span>: <span class="tok-str">"SUSPICIOUS"</span>,' },
        { num: 5, html: '  <span class="tok-str">"confidence"</span>: <span class="tok-num">0.882</span>,' },
        { num: 6, html: '  <span class="tok-str">"events_correlated"</span>: <span class="tok-num">5</span>,' },
        { num: 7, html: '  <span class="tok-str">"mitre_techniques"</span>: [<span class="tok-str">"T1059.003"</span>, <span class="tok-str">"T1053"</span>, <span class="tok-str">"T1003"</span>]' },
        { num: 8, html: '}' },
      ],
    },
  };

  function renderCode() {
    const sc = scenarios[activeScenario];
    const lines = sc[activeTab] || sc.python;

    gutters.innerHTML = lines.map((l) => `<span>${l.num}</span>`).join("");
    codePane.innerHTML = lines
      .map((l) => `<span class="code-line" data-line="${l.num}">${l.html || "&nbsp;"}</span>`)
      .join("");
    timingBadge.textContent = sc.timing;
  }

  function getRawCodeText() {
    const sc = scenarios[activeScenario];
    const lines = sc[activeTab] || sc.python;
    return lines
      .map((l) => {
        const tmp = document.createElement("div");
        tmp.innerHTML = l.html;
        return tmp.textContent || "";
      })
      .join("\n");
  }

  function runSimulation() {
    if (isRunning) return;
    isRunning = true;
    runBtn.classList.add("running");
    runBtn.querySelector(".run-text").textContent = "Running...";

    const sc = scenarios[activeScenario];
    streamLines.innerHTML = "";

    const codeLines = codePane.querySelectorAll(".code-line");
    codeLines.forEach((l) => l.classList.remove("active-executing"));

    const totalSteps = sc.steps.length;
    let stepIdx = 0;

    function step() {
      if (stepIdx < totalSteps) {
        const s = sc.steps[stepIdx];

        // Highlight active executing line in code
        codeLines.forEach((l) => l.classList.remove("active-executing"));
        const targetLineNum = stepIdx === 0 ? 2 : stepIdx === 1 ? 4 : stepIdx === 2 ? 7 : 8;
        const lineEl = codePane.querySelector(`[data-line="${targetLineNum}"]`);
        if (lineEl) lineEl.classList.add("active-executing");

        // Add stream line with smooth entrance
        const div = document.createElement("div");
        div.className = "stream-line";
        div.innerHTML = `<span class="stream-tag">${esc(s.tag)}</span><span class="stream-msg">${esc(s.msg)}</span>`;
        streamLines.appendChild(div);

        stepIdx++;
        setTimeout(step, 300);
      } else {
        // Final verdict line
        codeLines.forEach((l) => l.classList.remove("active-executing"));
        const lastLine = codePane.querySelector(`[data-line="10"]`) || codePane.querySelector(`[data-line="9"]`);
        if (lastLine) lastLine.classList.add("active-executing");

        const vDiv = document.createElement("div");
        vDiv.className = "stream-line final-verdict-line";
        vDiv.innerHTML = `
          <span class="verdict-arrow">→</span>
          <span class="term-verdict-badge ${sc.verdictClass}">${sc.verdictText}</span>
          <span class="term-verdict-detail">${esc(sc.verdictDetail)}</span>
        `;
        streamLines.appendChild(vDiv);

        setTimeout(() => {
          if (lastLine) lastLine.classList.remove("active-executing");
          runBtn.classList.remove("running");
          runBtn.querySelector(".run-text").textContent = "Replay";
          isRunning = false;
        }, 500);
      }
    }

    step();
  }

  // Copy button handler
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      try {
        const text = getRawCodeText();
        await navigator.clipboard.writeText(text);
        const copyTextEl = copyBtn.querySelector(".copy-text");
        const originalText = copyTextEl.textContent;
        copyTextEl.textContent = "Copied!";
        setTimeout(() => {
          copyTextEl.textContent = originalText;
        }, 1800);
      } catch (err) {
        showToast("Copied code to clipboard");
      }
    });
  }

  // Run button handler
  if (runBtn) {
    runBtn.addEventListener("click", () => {
      runSimulation();
    });
  }

  // Tab switching
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeTab = btn.getAttribute("data-tab");
      renderCode();
    });
  });

  // Target scenario switching
  targetPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      targetPills.forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      activeScenario = pill.getAttribute("data-target-case");
      renderCode();
      runSimulation();
    });
  });

  // Initial render
  renderCode();
  runSimulation();

  // Auto-run when scrolled into view
  if ("IntersectionObserver" in window) {
    const termObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasAutoRun) {
            hasAutoRun = true;
            runSimulation();
          }
        });
      },
      { threshold: 0.3 }
    );
    termObserver.observe(terminal);
  }
}

/* ---------- Init & Boot ---------- */
probeHealth();
setInterval(probeHealth, 15000);
loadSamplesCatalog();
initNavigation();
initPipelineTerminal();

// Auto-scan if deep link has ?path=...
const initial = new URLSearchParams(location.search).get("path");
if (initial && initial !== "/dev/null") {
  input.value = initial;
  executeScan(initial, scanMode);
} else {
  input.focus();
}

