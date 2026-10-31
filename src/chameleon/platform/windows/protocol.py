import os
import re
import secrets
import time
from pathlib import Path

from chameleon.core.schemas import Plan
from chameleon.platform.windows.shells import CmdAdapter


def action_directory(root: Path) -> Path:
    directory = root / "runtime" / "actions"
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.iterdir():
        if path.suffix not in (".cmd", ".response"):
            continue
        if time.time() - path.stat().st_mtime > 900:
            path.unlink(missing_ok=True)
    return directory


def emit_cmd(plan: Plan, cwd: Path, root: Path) -> str:
    adapter = CmdAdapter(plan.policy_token)
    commands = [adapter.render(a, cwd) for a in plan.actions]
    token = secrets.token_hex(16)
    directory = action_directory(root)
    path = directory / f"{token}.cmd"
    # Every command line hides its echo, independent of the user's echo setting.
    lines = [
        "@setlocal DisableDelayedExpansion",
        '@for /f "tokens=2 delims=:" %%C in (\'chcp\') do @set "_chameleon_cp=%%C"',
        "@chcp 65001 >nul",
    ]
    exports: list[str] = []
    for action, command in zip(plan.actions, commands, strict=True):
        if action.kind == "env":
            # Export after closing the local scope. Delayed expansion values are unsafe here.
            if "!" in action.value:
                raise ValueError("CMD: usa PowerShell para variables que contienen !")
            exports.append(command)
            continue
        else:
            if action.kind == "command" and re.match(
                r"""\s*(?:"[^"]+\.(?:cmd|bat)"|'[^']+\.(?:cmd|bat)'|\S+\.(?:cmd|bat))(?:\s|$)""",
                command,
                re.I,
            ):
                command = "call " + command
            # Model commands target interactive CMD; FOR variables need the
            # batch spelling inside this transient execution bridge.
            if action.kind == "command" and re.match(r"\s*for\b", command, re.I):
                variable = re.search(r"%{1,2}([A-Za-z])\s+in\b", command, re.I)
                if variable:
                    command = re.sub(
                        r"(?<!%)%" + re.escape(variable[1]) + r"(?![A-Za-z0-9_]*%)",
                        "%%" + variable[1],
                        command,
                    )
            lines.append("@" + command)
        lines.extend(["@if errorlevel 1 goto chameleon_error"])
    export_text = " & ".join(exports)
    finish = (
        '@endlocal & cd /d "%_chameleon_cwd%" & '
        + (export_text + " & " if export_text else "")
        + "exit /b 0"
    )
    lines.extend(
        [
            "@chcp %_chameleon_cp% >nul",
            '@set "_chameleon_cwd=%CD%"',
            finish,
            ":chameleon_error",
            "@chcp %_chameleon_cp% >nul",
            "@endlocal & exit /b 1",
        ]
    )
    content = ("\r\n".join(lines) + "\r\n").encode("utf-8")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
    return token
