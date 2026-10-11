"""Exercise distributable executables and their actual parent-shell integrations."""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from chameleon.core.config import Config, save_config
from chameleon.platform.windows.installer import install, remove_installation, uninstall_integration
from chameleon.platform.windows.shells import ps_quote
from chameleon.platform.windows.system import shell_executable

repo = Path(__file__).resolve().parents[1]
evidence = repo / "artifacts" / "frozen"
evidence.mkdir(parents=True, exist_ok=True)


def run(args: list[str], env: dict[str, str], cwd: Path, timeout: int = 90) -> str:
    result = subprocess.run(
        args,
        env=env,
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr + f"\nExit: {result.returncode}")
    return result.stdout + result.stderr


with tempfile.TemporaryDirectory(prefix="chameleon-frozen-") as directory:
    temp = Path(directory)
    root = temp / "Chameleon Niño"
    target = temp / "destino con espacios ñ"
    target.mkdir()
    profile = temp / "profile.ps1"
    original = b"# Existing profile retained\r\n"
    profile.write_bytes(original)
    install(root, repo / "dist" / "Chameleon", profiles=[profile], integrate=False)
    env = dict(os.environ, CHAMELEON_HOME=str(root), CHAMELEON_NONINTERACTIVE="1")
    # Simulate a destination with no Python/Node developer tools on PATH.
    windows = Path(os.environ["SystemRoot"])
    env["PATH"] = (
        str(windows / "System32") + ";" + str(windows / "System32" / "WindowsPowerShell" / "v1.0")
    )
    for variable in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
        env.pop(variable, None)
    checks = []
    version = run([str(root / "core" / "ChameleonCore.exe"), "version"], env, temp)
    assert "0.3.0" in version
    checks.append("Frozen Core version")
    if "--ai" in sys.argv:
        config = Config()
        config.ai.timeout = 180
        save_config(config, root)
        (target / "large-verified.py").write_bytes(b"#" * 1100000)
        (target / "small-verified.py").write_text("# small", encoding="utf-8")
        plan_text = run(
            [
                str(root / "core" / "ChameleonCore.exe"),
                "ai",
                "--dry-run",
                "busca todos los archivos python mayores de 1 MB",
            ],
            env,
            target,
            200,
        )
        encoded = re.search(r"--encoded ([A-Za-z0-9+/=]+)", plan_text)
        assert encoded is not None, plan_text
        action = json.loads(base64.b64decode(encoded.group(1)))
        assert action["kind"] == "find" and action["min_size_bytes"] >= 1000000
        output = run(
            [str(root / "core" / "ChameleonCore.exe"), "query", "--encoded", encoded.group(1)],
            env,
            target,
        )
        assert "large-verified.py" in output and "small-verified.py" not in output
        checks.append("Frozen Qwen schema, safety and actual size-filtered query")
    script = temp / "test.cmd"
    script.write_text(
        f'@echo off\r\nchcp 65001 >nul\r\ncall "{root / "bin" / "chameleon.cmd"}" ai ve a "{target}"\r\necho RESULT:%CD%\r\n',
        encoding="utf-8",
    )
    result = run(["cmd.exe", "/d", "/c", str(script)], env, temp)
    assert "RESULT:" + str(target) in result and "cd /d" not in result
    assert not list((root / "runtime" / "actions").glob("*.cmd"))
    checks.append("Frozen CMD parent cwd and temporary cleanup")
    for shell in ("powershell", "pwsh"):
        try:
            executable = shell_executable(shell)
        except OSError:
            continue
        command = (
            "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Import-Module "
            + ps_quote(str(root / "bin" / "Chameleon.psm1"))
            + "; chameleon ai 've a' "
            + ps_quote(str(target))
            + "; 'RESULT:'+(Get-Location).Path"
        )
        result = run([executable, "-NoProfile", "-Command", command], env, temp)
        assert "RESULT:" + str(target) in result
        checks.append("Frozen " + shell + " parent cwd")
    for shell in ("cmd", "powershell"):
        config = Config()
        config.terminal.shell = shell
        config.terminal.start_directory = str(temp)
        # A missing model exercises AI OFFLINE without interfering with host Ollama.
        if shell == "cmd":
            config.ai.model = "chameleon-test-model-missing:latest"
        save_config(config, root)
        output = evidence / shell
        run([str(root / "core" / "ChameleonTerminal.exe"), "--smoke", str(output)], env, temp, 60)
        assert json.loads((output / "frozen-terminal.json").read_text())["ok"]
        checks.append(
            "Frozen Qt/xterm/ConPTY " + shell + (" AI unavailable" if shell == "cmd" else "")
        )
    # Exercises extraction of the embedded payload and Qt Setup/Settings startup.
    run(
        [str(repo / "dist" / "ChameleonSetup.exe"), "--smoke", str(evidence / "setup")],
        env,
        temp,
        180,
    )
    assert json.loads((evidence / "setup" / "frozen-setup.json").read_text())["ok"]
    checks.append("Self extracting installer, Setup and Settings")
    for scale in ("1.25", "1.5"):
        config = Config()
        config.terminal.start_directory = str(temp)
        config.ai.enabled = False
        save_config(config, root)
        output = evidence / ("dpi-" + scale)
        run(
            [str(root / "core" / "ChameleonTerminal.exe"), "--smoke", str(output)],
            dict(env, QT_SCALE_FACTOR=scale),
            temp,
            60,
        )
        assert json.loads((output / "frozen-terminal.json").read_text())["ok"]
        checks.append("Frozen renderer with Qt scale factor " + scale)
    uninstall_integration(root, integrate=False)
    assert profile.read_bytes() == original
    remove_installation(root)
    checks.append("Frozen payload uninstalled; original profile retained")
    (evidence / "results.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    for check in checks:
        print("PASS: " + check)
