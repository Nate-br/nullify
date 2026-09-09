"""Shared pytest fixtures — synthetic targets only, never real malware."""

from __future__ import annotations

import pytest

from nullify.core.models import FileTarget, LogTarget


@pytest.fixture
def benign_file(tmp_path) -> FileTarget:
    p = tmp_path / "benign.txt"
    p.write_bytes(b"hello world " * 64)
    return FileTarget(p)


@pytest.fixture
def pe_like_file(tmp_path) -> FileTarget:
    """Fake PE: MZ header, plausible import names, high-entropy tail."""
    blob = bytearray(b"MZ" + b"\x00" * 62)
    imports = (b"CreateRemoteThread\00URLDownloadToFile\00CryptEncrypt\00"
               b"FindFirstFile\00SetWindowsHookEx\00GetAsyncKeyState\00")
    blob += imports
    blob += b"\x00" * 64
    blob += bytes(range(256)) * 32  # high-entropy tail
    p = tmp_path / "sample.exe"
    p.write_bytes(bytes(blob))
    return FileTarget(p)


@pytest.fixture
def trojan_like_file(tmp_path) -> FileTarget:
    """PE with trojan-ish imports + a Run-key persistence string."""
    blob = bytearray(b"MZ" + b"\x00" * 62)
    blob += b"CreateRemoteThread\00WinExec\00URLDownloadToFile\00"
    blob += b"Software\\Microsoft\\Windows\\CurrentVersion\\Run\x00"
    p = tmp_path / "trojanish.exe"
    p.write_bytes(bytes(blob))
    return FileTarget(p)


@pytest.fixture
def sysmon_log(tmp_path) -> LogTarget:
    lines = [
        '{"event": "Process Create", "image": "C:\\\\Windows\\\\system32\\\\cmd.exe"}',
        '{"event": "Process Create", "image": "C:\\\\Users\\\\pub\\\\AppData\\\\Temp\\\\dropper.exe"}',
        '{"event": "Process Create", "image": "C:\\\\Windows\\\\system32\\\\schtasks.exe /create /tn updater"}',
        '{"event": "Registry", "target": "HKCU\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run\\\\updater"}',
        "not-json-line-should-be-skipped",
    ]
    p = tmp_path / "sysmon.jsonl"
    p.write_text("\n".join(lines), encoding="utf-8")
    return LogTarget(p)


@pytest.fixture
def missing_file(tmp_path) -> FileTarget:
    return FileTarget(tmp_path / "does_not_exist.exe")
