import os
import subprocess
from pathlib import Path

import pytest

from chameleon.core.schemas import Action, Plan
from chameleon.platform.windows.protocol import emit_cmd


@pytest.mark.windows
def test_interactive_for_variables_and_environment_survive_batch_bridge(tmp_path: Path) -> None:
    plan = Plan(
        intent="execute",
        shell="cmd",
        summary="loop",
        actions=[
            Action(kind="command", command="for %i in (one two) do @echo %i-%CHAMELEON_QA_VALUE%")
        ],
    )
    token = emit_cmd(plan, tmp_path, tmp_path)
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(tmp_path / "runtime/actions" / (token + ".cmd"))],
        cwd=tmp_path,
        env=dict(os.environ, CHAMELEON_QA_VALUE="ALPHA"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert result.returncode == 0 and "one-ALPHA" in result.stdout and "two-ALPHA" in result.stdout


@pytest.mark.windows
def test_existing_cmd_script_returns_to_bridge_and_parent_cwd(tmp_path: Path) -> None:
    script = tmp_path / "hello script.cmd"
    script.write_text("@echo SCRIPT_05_OK\n", encoding="ascii")
    plan = Plan(
        intent="execute",
        shell="cmd",
        summary="script",
        actions=[
            Action(kind="command", command='"' + str(script) + '"'),
            Action(kind="command", command="echo AFTER_SCRIPT_05"),
        ],
    )
    token = emit_cmd(plan, tmp_path, tmp_path)
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(tmp_path / "runtime/actions" / (token + ".cmd"))],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert (
        result.returncode == 0
        and "SCRIPT_05_OK" in result.stdout
        and "AFTER_SCRIPT_05" in result.stdout
    )
