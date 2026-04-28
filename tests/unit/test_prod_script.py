"""Tests for test_prod.py safeguards."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TEST_PROD = Path(__file__).parent.parent.parent / "test_prod.py"


def test_prod_script_refuses_missing_contract():
    env = {
        "CSOB_CLIENT_APP_GUID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "PATH": "",
    }
    # Keep PATH so python can be found
    env["PATH"] = "/usr/bin:/bin"
    result = subprocess.run(
        [sys.executable, str(TEST_PROD)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1
    assert "CSOB_CONTRACT" in result.stdout


def test_prod_script_refuses_missing_guid():
    env = {
        "CSOB_CONTRACT": "123456",
        "PATH": "/usr/bin:/bin",
    }
    result = subprocess.run(
        [sys.executable, str(TEST_PROD)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1
    assert "CSOB_CLIENT_APP_GUID" in result.stdout
