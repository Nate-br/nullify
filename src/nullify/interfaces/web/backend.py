"""FastAPI backend — week 13 milestone.

Must wrap the shared Orchestrator (PLAN.md §4.3):
  * POST /api/scan      — file upload → AnalysisResult
  * GET /api/health   — health status
"""

from __future__ import annotations

from pathlib import Path

API_VERSION = "0.1.0"

try:  # pragma: no cover — exercised in week 13
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel

    from nullify.core.models import FileTarget, ScanMode
    from nullify.core.orchestrator import Orchestrator

    app = FastAPI(title="Nullify API", version=API_VERSION)

    class ScanRequest(BaseModel):
        path: str

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/scan")
    def scan(req: ScanRequest) -> dict:
        target = FileTarget(Path(req.path))
        orch = Orchestrator()
        result = orch.run(target, ScanMode.STATIC_ONLY)
        return result.to_dict()

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return """<!DOCTYPE html>
<html>
<head>
    <title>Nullify Web UI</title>
    <style>
        body { font-family: sans-serif; margin: 2rem; max-width: 800px; }
        .banner { padding: 1rem; margin-bottom: 1rem; border-radius: 4px; font-weight: bold; }
        .malicious { background-color: #ffebee; color: #c62828; }
        .suspicious { background-color: #fff8e1; color: #f57f17; }
        .benign { background-color: #e8f5e9; color: #2e7d32; }
        .finding { padding: 0.5rem; border: 1px solid #ccc; margin-bottom: 0.5rem; }
        .badge { font-size: 0.8em; padding: 2px 4px; border-radius: 2px; color: white; }
        .badge.critical { background: red; }
        .badge.high { background: orange; }
        .badge.medium { background: #ffcc00; color: black; }
        .badge.low { background: #4fc3f7; color: black; }
        .badge.info { background: gray; }
    </style>
</head>
<body>
    <h1>Nullify Web UI</h1>
    <div>
        <input type="text" id="path-input" placeholder="/path/to/file.exe" style="width: 300px;">
        <button id="scan-btn">Scan</button>
    </div>
    <div id="loading" style="display: none; margin-top: 1rem;">Scanning...</div>
    <div id="results" style="margin-top: 2rem;"></div>

    <script>
        document.getElementById('scan-btn').onclick = async () => {
            const path = document.getElementById('path-input').value;
            if (!path) return;
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').innerHTML = '';
            
            try {
                const res = await fetch('/api/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: path })
                });
                const data = await res.json();
                
                let html = '';
                const v = data.verdict;
                let vClass = 'banner';
                if (v === 'malicious') vClass += ' malicious';
                else if (v === 'suspicious') vClass += ' suspicious';
                else if (v === 'benign') vClass += ' benign';
                
                html += `<div class="${vClass}">Verdict: ${v.toUpperCase()} (${data.malware_type}) - ${(data.confidence * 100).toFixed(1)}%</div>`;
                
                html += '<h3>Agents Progress</h3><ul>';
                data.agents.forEach(a => {
                    html += `<li>${a.agent}: ${a.status} (${a.duration_s}s)</li>`;
                });
                html += '</ul>';
                
                html += '<h3>Findings</h3>';
                data.agents.forEach(a => {
                    a.findings.forEach(f => {
                        let sev = f.severity;
                        html += `<div class="finding">
                            <strong>${f.title}</strong>
                            <span class="badge ${sev}">${sev}</span>
                            <br><small>${f.agent}</small>
                        </div>`;
                    });
                });
                
                document.getElementById('results').innerHTML = html;
            } catch (err) {
                document.getElementById('results').innerHTML = `<div style="color:red">Error: ${err}</div>`;
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        };
    </script>
</body>
</html>
"""

except ModuleNotFoundError:  # fastapi not installed — CLI/tests must not care
    app = None  # type: ignore[assignment]
