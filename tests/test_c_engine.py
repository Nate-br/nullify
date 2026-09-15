import json
import math
import subprocess
from pathlib import Path

import pytest

from nullify.core import c_engine
from nullify.core.ember_features import ByteEntropyHistogram, StringExtractor
from nullify.core.models import FileTarget


def test_c_engine_is_accelerated():
    assert c_engine.is_c_accelerated() is True


def test_c_entropy_calculations():
    # Empty
    assert c_engine.fast_entropy(b"") == 0.0

    # Uniform (all same bytes -> 0 entropy)
    assert c_engine.fast_entropy(b"A" * 1000) == 0.0

    # Max theoretical entropy for 256 distinct uniform bytes (8.0)
    all_bytes = bytes(range(256)) * 10
    h = c_engine.fast_entropy(all_bytes)
    assert abs(h - 8.0) < 1e-6

    # Test arbitrary text
    sample = b"Nullify Threat Intelligence C-Core Engine Acceleration Test"
    # Python calculation
    counts = {}
    for b in sample:
        counts[b] = counts.get(b, 0) + 1
    py_h = -sum((c / len(sample)) * math.log2(c / len(sample)) for c in counts.values())
    c_h = c_engine.fast_entropy(sample)
    assert abs(py_h - c_h) < 1e-6


def test_c_byte_entropy_histogram_parity():
    sample = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00" * 200
    beh = ByteEntropyHistogram()
    py_matrix = beh.raw_features(sample, None)
    c_matrix = c_engine.fast_byte_entropy_histogram(sample, beh.step, beh.window)

    assert c_matrix is not None
    assert len(c_matrix) == 256
    assert c_matrix == py_matrix


def test_c_extract_strings_parity():
    sample = (
        b"MZ\x00\x00This is a test string for EMBER feature extraction\x00"
        b"C:\\Windows\\System32\\cmd.exe\x00\x00"
        b"https://malicious-domain.xyz/payload.exe\x00\x00"
        b"HKEY_LOCAL_MACHINE\\Software\\Microsoft\x00\x00"
        b"short\x00"
    )

    se = StringExtractor()
    py_res = se.raw_features(sample, None)
    c_res = c_engine.fast_extract_strings(sample)

    assert c_res is not None
    assert c_res["numstrings"] == py_res["numstrings"]
    assert abs(c_res["avlength"] - py_res["avlength"]) < 1e-5
    assert c_res["printables"] == py_res["printables"]
    assert c_res["printabledist"] == py_res["printabledist"]
    assert abs(c_res["entropy"] - py_res["entropy"]) < 1e-5
    assert c_res["paths"] == py_res["paths"]
    assert c_res["urls"] == py_res["urls"]
    assert c_res["registry"] == py_res["registry"]
    assert c_res["MZ"] == py_res["MZ"]


def test_c_triage_file(tmp_path: Path):
    test_file = tmp_path / "sample.bin"
    test_file.write_bytes(b"\x7fELF" + b"\x02\x01\x01\x00" + b"\x00" * 10 + b"\x3e\x00" + b"\x00" * 100)

    res = c_engine.fast_triage_file(test_file)
    assert res is not None
    assert res["magic"] == "elf"
    assert "AMD64" in res["architecture"] or "ELF" in res["architecture"]
    assert res["is_executable"] is True
    assert len(res["md5"]) == 32
    assert len(res["sha256"]) == 64


def test_c_cli_standalone(tmp_path: Path):
    cli_bin = Path("bin/nullify-core")
    assert cli_bin.exists()

    test_file = tmp_path / "sample.elf"
    test_file.write_bytes(b"\x7fELF" + b"\x02\x01\x01" + b"\x00" * 100)

    # Standard text mode
    res = subprocess.run([str(cli_bin), str(test_file)], capture_output=True, text=True, check=True)
    assert "NULLIFY C-CORE ACCELERATOR" in res.stdout
    assert "ELF" in res.stdout

    # JSON mode
    res_json = subprocess.run([str(cli_bin), str(test_file), "--json"], capture_output=True, text=True, check=True)
    data = json.loads(res_json.stdout)
    assert data["path"] == str(test_file)
    assert data["magic"] == "ELF (Executable and Linkable Format)"
    assert data["is_executable"] is True
    assert "md5" in data
    assert "sha256" in data
    assert "triage_latency_ms" in data


def test_models_file_target_uses_fast_entropy(tmp_path: Path):
    p = tmp_path / "payload.exe"
    p.write_bytes(b"A" * 5000)
    target = FileTarget(p)
    assert target.entropy() == 0.0


def test_c_fast_hashes_parity(tmp_path: Path):
    sample = b"Nullify Native C Cryptographic Hashing Test Payload 12345"
    p = tmp_path / "hash_test.bin"
    p.write_bytes(sample)

    import hashlib
    py_md5 = hashlib.md5(sample).hexdigest()
    py_sha1 = hashlib.sha1(sample).hexdigest()
    py_sha256 = hashlib.sha256(sample).hexdigest()

    c_hashes = c_engine.fast_hashes_file(p)
    assert c_hashes["md5"] == py_md5
    assert c_hashes["sha1"] == py_sha1
    assert c_hashes["sha256"] == py_sha256


def test_c_byte_histogram_parity():
    import numpy as np
    data = bytes(range(256)) * 4 + b"\x00\x00\x00\xff"
    py_hist = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256).tolist()
    c_hist = c_engine.fast_byte_histogram(data)
    assert py_hist == c_hist


def test_c_pe_imports_and_hints():
    sample = b"MZ" + b"\x00" * 62 + b"CreateRemoteThread\x00WinExec\x00URLDownloadToFile\x00"
    res = c_engine.fast_parse_pe_imports(sample)
    assert res is not None
    assert res["type_votes"]["trojan"] == 3
    apis = [api for api, _ in res["matched_apis"]]
    assert "CreateRemoteThread" in apis
    assert "WinExec" in apis
    assert "URLDownloadToFile" in apis


def test_c_pattern_scanner():
    sample = (
        b"MZ\x00\x00"
        b"Software\\Microsoft\\Windows\\CurrentVersion\\Run\x00"
        b"powershell.exe -enc aW52b2tl\x00"
        b"readme for decrypt send btc\x00"
        b"C:\\Windows\\Temp\\payload.exe\x00"
    )
    res = c_engine.fast_scan_patterns(sample)
    assert res is not None
    titles = [t for t, _, _ in res["matches"]]
    assert "Registry Run-key persistence" in titles
    assert "PowerShell download cradle" in titles
    assert "Executable drop path" in titles
    assert "Ransom note string" in titles


def test_c_pattern_scanner_no_false_positives():
    # Standalone 3-letter sequence 'xmr' and single word 'encrypted' must not trigger ransom note
    sample = b"This is unencrypted normal data with a variable named xmr and monero in comments."
    res = c_engine.fast_scan_patterns(sample)
    assert res is not None
    titles = [t for t, _, _ in res["matches"]]
    assert "Ransom note string" not in titles

    # Real ransom note phrase must trigger
    ransom_sample = b"Attention: all your files have been encrypted! Send btc to recover."
    res2 = c_engine.fast_scan_patterns(ransom_sample)
    assert res2 is not None
    titles2 = [t for t, _, _ in res2["matches"]]
    assert "Ransom note string" in titles2


