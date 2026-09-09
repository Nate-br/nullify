"""Tests for the Textual TUI."""

from __future__ import annotations

import asyncio

import pytest

from nullify.interfaces.cli.tui.app import NullifyTUI


@pytest.mark.asyncio
async def test_tui_benign_scan(benign_file):
    app = NullifyTUI(target_path=str(benign_file.path), deep=False)
    async with app.run_test() as pilot:
        # 1. App mounts and shows header
        assert app.query_one("Header") is not None
        
        # 2. Wait for the worker thread to finish the scan
        # We check the verdict banner periodically
        verdict_found = False
        for _ in range(50):
            banner = app.query_one("#verdict_banner")
            banner_text = str(banner.render())
            if "BENIGN" in banner_text.upper():
                verdict_found = True
                break
            await asyncio.sleep(0.1)
            
        assert verdict_found, "Scan did not complete or display BENIGN verdict in time"
        
        # 3. Quit works
        await pilot.press("q")
