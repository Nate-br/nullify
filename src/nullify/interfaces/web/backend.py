"""FastAPI backend — Nullify's web interface.

Serves the single-page frontend from ``static/`` and wraps the shared
Orchestrator (PLAN.md §4.3): every interface calls ``Orchestrator.run()``
and consumes the same ``AnalysisResult`` — the web UI never re-implements
analysis logic.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from nullify.core.models import FileTarget, ScanMode
from nullify.core.orchestrator import Orchestrator
from nullify.interfaces.web import chat

API_VERSION = "0.1.0"
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Nullify API", version=API_VERSION, docs_url="/api/docs")


class ScanRequest(BaseModel):
    path: str


class ChatRequest(BaseModel):
    message: str
    include_context: bool = True


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/scan")
def scan(req: ScanRequest) -> dict:
    """Run the full pipeline on a local file path and return the report."""
    target = FileTarget(Path(req.path))
    orch = Orchestrator()
    result = orch.run(target, ScanMode.STATIC_ONLY)
    report = result.to_dict()
    chat.last_report = report
    return report


@app.post("/api/chat")
def chat_api(req: ChatRequest):
    engine = chat.ChatEngine()
    if not engine.available():
        return JSONResponse(
            status_code=503,
            content={"error": "chat model not available — run: uv sync --extra llm and place the gguf in models/llm/"}
        )

    system_prompt = (
        "you are nullify's analysis assistant. explain malware analysis verdicts, "
        "findings, mitre attack techniques and agent results. be concise and factual. "
        "if scan context is provided, ground your answer in it."
    )
    messages = [{"role": "system", "content": system_prompt}]

    if req.include_context and chat.last_report is not None:
        rep = chat.last_report
        verdict = rep.get("verdict", "unknown")
        confidence = rep.get("confidence", 0.0)
        malware_type = rep.get("malware_type", "unknown")
        mitre_ids = rep.get("mitre_ids", [])
        
        findings_info = []
        for a in rep.get("agents", []):
            for f in a.get("findings", []):
                findings_info.append(f"{f.get('title', 'unknown')} ({f.get('severity', 'info')})")
        
        context_str = f"SCAN CONTEXT:\nVerdict: {verdict}\nConfidence: {confidence}\nType: {malware_type}\nMITRE IDs: {', '.join(mitre_ids)}\nTop Findings: {', '.join(findings_info[:10])}"
        messages.append({"role": "user", "content": context_str})
    
    messages.append({"role": "user", "content": req.message})

    try:
        reply = engine.generate(messages)
        return {"reply": reply}
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.exception_handler(FileNotFoundError)
def not_found(_req, exc: FileNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": f"file not found: {exc.filename or exc}"})


@app.exception_handler(PermissionError)
def not_permitted(_req, exc: PermissionError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"error": f"permission denied: {exc}"})


@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
