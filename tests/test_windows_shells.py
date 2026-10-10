import os
import subprocess
from pathlib import Path

import pytest

from chameleon.platform.windows.shells import ps_quote
from chameleon.platform.windows.system import shell_executable

pytestmark = pytest.mark.windows


@pytest.mark.parametrize(
    "name",
    [
        "subfolder",
        "Prueba con espacios",
        "Español Niño",
        "percent%test",
        "bang!test",
        "amp&test",
        "caret^test",
        "paren(test)",
    ],
)
@pytest.mark.parametrize("delayed", ["off", "on"])
def test_cmd_cd_persists(shell_install: Path, tmp_path: Path, name: str, delayed: str) -> None:
    target = tmp_path / name
    target.mkdir()
    script = tmp_path / "check.cmd"
    # Caller passes natural language; percent must be escaped in any user batch too.
    script.write_text(
        f'@echo off\r\nchcp 65001 >nul\r\ncall "{shell_install / "bin" / "chameleon.cmd"}" ai ve a "%%CHAMELEON_TEST_TARGET%%"\r\necho RESULT:"%CD%"\r\n',
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["CHAMELEON_TEST_TARGET"] = str(target)
    # Parent delayed expansion cannot preserve ! in literal requests; use a variable
    # expanded under the wrapper's disabled delayed expansion instead (documented CMD rule).
    if delayed == "on" and "!" in name:
        pytest.skip("CMD caller expands ! before invocation when /v:on; shell limitation")
    result = subprocess.run(
        ["cmd.exe", "/d", f"/v:{delayed}", "/c", script.name],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert 'RESULT:"' + str(target) + '"' in result.stdout, result.stdout + result.stderr
    assert "cd /d" not in result.stdout
    assert not list((shell_install / "runtime" / "actions").glob("*.cmd"))


@pytest.mark.parametrize("shell", ["powershell", "pwsh"])
def test_powershell_cd_persists(shell_install: Path, tmp_path: Path, shell: str) -> None:
    try:
        executable = shell_executable(shell)
    except OSError:
        pytest.skip("PowerShell 7 not installed")
    target = tmp_path / "Español Niño ' & ! % con espacios"
    target.mkdir()
    script = (
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Import-Module "
        + ps_quote(str(shell_install / "bin" / "Chameleon.psm1"))
        + "; chameleon ai 've a' "
        + ps_quote(str(target))
        + "; 'RESULT:'+(Get-Location).Path"
    )
    result = subprocess.run(
        [executable, "-NoProfile", "-Command", script],
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    assert "RESULT:" + str(target) in result.stdout, result.stdout + result.stderr


def test_cmd_dry_run_never_executes(shell_install: Path, tmp_path: Path) -> None:
    target = tmp_path / "subfolder"
    target.mkdir()
    script = tmp_path / "check.cmd"
    script.write_text(
        f'@echo off\r\ncall "{shell_install / "bin" / "chameleon.cmd"}" ai --dry-run ve a subfolder\r\necho RESULT:%CD%\r\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "RESULT:" + str(tmp_path) in result.stdout


def test_deletion_default_no(shell_install: Path, tmp_path: Path) -> None:
    victim = tmp_path / "old.txt"
    victim.write_text("keep", encoding="utf-8")
    result = subprocess.run(
        [
            str(shell_install / "core" / "ChameleonCore.exe"),
            "--emit",
            "cmd",
            "ai",
            "elimina",
            str(victim),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1 and victim.read_text() == "keep"
