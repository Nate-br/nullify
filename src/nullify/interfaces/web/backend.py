"""FastAPI backend — week 13 milestone stub.

Must wrap the shared Orchestrator (AGENTS.md rule #1):
  * POST /scan      — file upload → AnalysisResult
  * WS   /ws/scan   — live agent-progress streaming (same EventBus)

Endpoints are intentionally not implemented yet; the module is import-safe
without fastapi installed so tests and the CLI never depend on it.
"""

from __future__ import annotations

API_VERSION = "0.1.0"

try:  # pragma: no cover — exercised in week 13
    from fastapi import FastAPI

    app = FastAPI(title="Nullify API", version=API_VERSION)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": API_VERSION}

except ModuleNotFoundError:  # fastapi not installed — CLI/tests must not care
    app = None  # type: ignore[assignment]
