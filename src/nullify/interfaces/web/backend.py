import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from nullify.core.models import FileTarget, LogTarget, ScanMode
from nullify.core.orchestrator import Orchestrator

API_VERSION = "0.1.0"
STATIC_DIR = Path(__file__).parent / "static"
UPLOAD_DIR = Path(tempfile.gettempdir()) / "nullify_web_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SAMPLES_DIR = Path(tempfile.gettempdir()) / "nullify_synthetic_samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Nullify API", version=API_VERSION, docs_url="/api/docs")


class ScanRequest(BaseModel):
    path: str
    mode: str = "static"


class RuleGenRequest(BaseModel):
    findings: list[dict[str, Any]] = []
    imports: list[str] = []
    family: str = "Trojan"
    name_hint: str = "Sample"


def _ensure_synthetic_samples() -> dict[str, str]:
    """Ensure safe synthetic sample fixtures exist for one-click testing."""
    samples = {}
    
    # 1. Trojan Dropper
    p_trojan = SAMPLES_DIR / "synthetic_trojan_dropper.exe"
    if not p_trojan.exists():
        blob = bytearray(b"MZ" + b"\x00" * 62)
        blob += (
            b"CreateRemoteThread\00WinExec\00URLDownloadToFile\00"
            b"Software\\Microsoft\\Windows\\CurrentVersion\\Run\x00"
        )
        blob += b"\x00" * 128
        p_trojan.write_bytes(bytes(blob))
    samples["trojan"] = str(p_trojan)

    # 2. Ransomware Sample
    p_ransom = SAMPLES_DIR / "synthetic_ransomware.exe"
    if not p_ransom.exists():
        blob = bytearray(b"MZ" + b"\x00" * 62)
        blob += (
            b"CryptEncrypt\00CryptGenKey\00FindFirstFile\00"
            b"README_FOR_DECRYPT.txt: your files have been encrypted\x00"
        )
        blob += b"\x00" * 128
        p_ransom.write_bytes(bytes(blob))
    samples["ransomware"] = str(p_ransom)

    # 3. Benign Sample
    p_benign = SAMPLES_DIR / "synthetic_benign_util.exe"
    if not p_benign.exists():
        blob = bytearray(b"MZ" + b"\x00" * 62)
        blob += b"Nullify synthetic benign test application.\x00"
        blob += b"Standard output string, no malicious imports.\x00"
        p_benign.write_bytes(bytes(blob))
    samples["benign"] = str(p_benign)

    # 4. Sysmon Log Sample
    p_log = SAMPLES_DIR / "synthetic_sysmon.jsonl"
    if not p_log.exists():
        lines = [
            '{"event": "Process Create", "image": "C:\\\\Windows\\\\system32\\\\cmd.exe"}',
            '{"event": "Process Create", "image": "C:\\\\Users\\\\pub\\\\AppData\\\\Temp\\\\dropper.exe"}',
            '{"event": "Process Create", "image": "C:\\\\Windows\\\\system32\\\\schtasks.exe /create /tn updater"}',
            '{"event": "Registry", "target": "HKCU\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run\\\\updater"}',
            '{"event": "LSASS Access", "image": "C:\\\\Windows\\\\system32\\\\lsass.exe"}',
        ]
        p_log.write_text("\n".join(lines), encoding="utf-8")
    samples["sysmon"] = str(p_log)

    return samples


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "version": API_VERSION, "engine": "XGBoost EMBER + YARA"}


@app.get("/api/samples")
def get_samples() -> dict[str, Any]:
    """Provide available synthetic demonstration samples."""
    samples = _ensure_synthetic_samples()
    return {
        "samples": [
            {
                "id": "trojan",
                "name": "synthetic_trojan_dropper.exe",
                "path": samples["trojan"],
                "badge": "Trojan / Persistence",
                "description": "PE with CreateRemoteThread, WinExec, and Registry Run-key persistence",
            },
            {
                "id": "ransomware",
                "name": "synthetic_ransomware.exe",
                "path": samples["ransomware"],
                "badge": "Ransomware / Crypt",
                "description": "PE with CryptEncrypt, CryptGenKey, and ransom note strings",
            },
            {
                "id": "benign",
                "name": "synthetic_benign_util.exe",
                "path": samples["benign"],
                "badge": "Benign Clean",
                "description": "Harmless PE file with no malicious API indicators or entropy anomalies",
            },
            {
                "id": "sysmon",
                "name": "synthetic_sysmon.jsonl",
                "path": samples["sysmon"],
                "badge": "Sysmon EVTX / Log",
                "description": "Behavioral log with temp path execution, scheduled tasks, and persistence",
            },
        ]
    }


@app.post("/api/scan")
def scan(req: ScanRequest) -> dict:
    """Run the full pipeline on a local file path and return the report."""
    path = Path(req.path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
        
    mode = ScanMode.DEEP if req.mode == "deep" else ScanMode.STATIC_ONLY

    # Detect log targets
    if path.suffix.lower() in (".jsonl", ".evtx", ".log"):
        target = LogTarget(path)
    else:
        target = FileTarget(path)

    orch = Orchestrator()
    result = orch.run(target, mode)
    return result.to_dict()


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), mode: str = "static") -> dict:
    """Upload a file directly to scan."""
    safe_name = Path(file.filename or "uploaded_sample.bin").name
    dest_path = UPLOAD_DIR / f"{time.time_ns()}_{safe_name}"
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    scan_req = ScanRequest(path=str(dest_path), mode=mode)
    return scan(scan_req)


@app.post("/api/generate-rule")
def generate_rule(req: RuleGenRequest) -> dict[str, str]:
    """Synthesize a YARA rule from findings."""
    from nullify.core.rulegen import from_findings

    rule_str = from_findings(
        findings=req.findings,
        imports=req.imports,
        family=req.family or "Malware",
        name_hint=req.name_hint or "Sample",
    )
    return {"rule": rule_str}


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

