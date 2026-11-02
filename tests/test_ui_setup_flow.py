import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.gui
@pytest.mark.parametrize("mode", ["fresh", "update"])
def test_setup_primary_action_and_consent(tmp_path: Path, mode: str) -> None:
    if os.name != "nt":
        pytest.skip("Windows GUI")
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("ui_setup_flow_check.py")), str(tmp_path), mode],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS:" in result.stdout
