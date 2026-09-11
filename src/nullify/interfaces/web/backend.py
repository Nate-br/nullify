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

API_VERSION = "0.1.0"
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Nullify API", version=API_VERSION, docs_url="/api/docs")


class ScanRequest(BaseModel):
    path: str


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/scan")
def scan(req: ScanRequest) -> dict:
    """Run the full pipeline on a local file path and return the report."""
    target = FileTarget(Path(req.path))
    orch = Orchestrator()
    result = orch.run(target, ScanMode.STATIC_ONLY)
    return result.to_dict()


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
