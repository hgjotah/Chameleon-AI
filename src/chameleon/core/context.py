import base64
import datetime
import json
import locale
import os
import platform
import re
import shutil
import subprocess
from functools import lru_cache
from itertools import islice
from pathlib import Path

from pydantic import BaseModel, Field

from chameleon.core.privacy import redact
from chameleon.core.schemas import ShellName
from chameleon.platform.windows.system import WindowsPlatform


class Context(BaseModel):
    os: str = Field(default_factory=platform.platform)
    shell: ShellName = "cmd"
    shell_version: str = "unknown"
    shell_executable: str = ""
    shell_edition: str = ""
    language_mode: str = ""
    architecture: str = Field(default_factory=platform.machine)
    locale: str = Field(default_factory=lambda: locale.getlocale()[0] or "unknown")
    environment: dict[str, str] = Field(default_factory=dict)
    cwd: str
    admin: bool = False
    system_directory: str = "C:\\Windows"
    known_directories: dict[str, str] = Field(default_factory=dict)
    entries: list[str] = Field(default_factory=list)
    executables: dict[str, str] = Field(default_factory=dict)
    recent: list[str] = Field(default_factory=list)
    observed_output: str = ""
    evidence: list[dict] = Field(default_factory=list)
    needs_verified_observation: bool = False
    action_kind_hint: str = ""
    requested_action: dict[str, str] = Field(default_factory=dict)
    permissions: dict[str, bool] = Field(default_factory=dict)
    current_time: str = Field(
        default_factory=lambda: datetime.datetime.now().astimezone().isoformat()
    )

    def model_payload(self, request: str) -> dict:
        data = self.model_dump()
        # Terminal escape sequences are control data, not useful linguistic context.
        visible = re.sub(
            r"\x1b(?:\][^\x07]*(?:\x07|\x1b\\)|\[[0-?]*[ -/]*[@-~])", "", self.observed_output
        )
        visible = "".join(c for c in visible if ord(c) >= 32 or c in "\r\n\t")
        data["observed_output"] = redact(visible)[-600:]
        data["recent"] = [redact(item)[:400] for item in self.recent[-4:]]
        data["entries"] = self.entries[:40]
        data["entries_complete"] = False
        observations = []
        budget = 12000
        for item in reversed(self.evidence[-8:]):
            observation = dict(item)
            if "content" in observation and len(observation["content"]) > 6000:
                observation["content"] = observation["content"][:6000]
                observation["truncated"] = True
            if len(observation.get("entries", [])) > 20:
                observation["entries"] = observation["entries"][:20]
                observation["complete"] = False
            size = len(json.dumps(observation, ensure_ascii=False))
            if size > budget:
                continue
            budget -= size
            observations.append(observation)
        data["evidence"] = list(reversed(observations))
        data["executables"] = {
            name: path
            for name, path in self.executables.items()
            if re.search(r"\b" + re.escape(name) + r"\b", request, re.I)
        }
        return {name: value for name, value in data.items() if value not in ("", [], {})}


def apply_shell_state(context: Context, encoded: str) -> None:
    """Accept bounded caller metadata, never execution policy or function bodies."""
    if len(encoded) > 16384:
        raise ValueError("Estado del shell demasiado grande.")
    state = json.loads(base64.b64decode(encoded, validate=True).decode("utf-8"))
    if not isinstance(state, dict):
        raise ValueError("Estado del shell inválido.")
    if isinstance(state.get("edition"), str):
        context.shell_edition = state["edition"][:80]
    if isinstance(state.get("language_mode"), str):
        context.language_mode = state["language_mode"][:80]
    commands = state.get("commands", [])
    if not isinstance(commands, list):
        raise ValueError("Lista de comandos del shell inválida.")
    for name in commands[:24]:
        if isinstance(name, str) and re.fullmatch(r"[\w.-]{1,128}", name):
            context.executables[name.casefold()] = "existing caller function/alias"


@lru_cache(maxsize=8)
def shell_facts(shell: ShellName, executable: str) -> dict[str, str]:
    """Read bounded, stable shell metadata. Never execute model-generated code."""
    if shell == "cmd":
        return {"shell_version": platform.version(), "shell_edition": "Windows CMD"}
    from chameleon.platform.windows.system import hidden_run

    try:
        result = hidden_run(
            [
                executable,
                "-NoLogo",
                "-NoProfile",
                "-Command",
                "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
                "@{shell_version=$PSVersionTable.PSVersion.ToString();"
                "shell_edition=$PSVersionTable.PSEdition;"
                "language_mode=$ExecutionContext.SessionState.LanguageMode.ToString();"
                "session_objects=(($Host.UI.RawUI.PSObject.Properties | ForEach-Object {'$Host.UI.RawUI.'+$_.Name+' ('+$_.TypeNameOfValue+')'}) -join '; ')} | ConvertTo-Json -Compress",
            ],
            timeout=4,
            encoding="utf-8",
        )
        return json.loads(result.stdout) if result.returncode == 0 else {}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}


def build_context(cwd: Path, shell: ShellName, recent: list[str] | None = None) -> Context:
    adapter = WindowsPlatform()
    entries: list[str] = []
    try:
        with os.scandir(cwd) as directory:
            entries = sorted(p.name + ("/" if p.is_dir() else "") for p in islice(directory, 100))
    except OSError:
        entries = []
    executable = (
        shutil.which({"cmd": "cmd.exe", "powershell": "powershell.exe", "pwsh": "pwsh.exe"}[shell])
        or ""
    )
    facts = shell_facts(shell, executable) if executable else {}
    return Context(
        shell=shell,
        shell_executable=executable,
        shell_version=facts.get("shell_version", "unknown"),
        shell_edition=facts.get("shell_edition", ""),
        language_mode=facts.get("language_mode", ""),
        cwd=str(cwd),
        admin=adapter.is_admin(),
        system_directory=adapter.system_directory(),
        known_directories=adapter.known_directories(),
        entries=entries,
        recent=[redact(s)[:1000] for s in (recent or [])[-6:]],
        # Allowlist only: never expose credentials or dump the environment/PATH.
        environment={
            name: os.environ[name]
            for name in ("USERPROFILE", "SystemRoot", "TEMP", "ProgramFiles", "ProgramFiles(x86)")
            if name in os.environ
        },
        executables={
            name: found
            for name in (
                "git",
                "python",
                "py",
                "node",
                "winget",
                "npm",
                "ssh",
                "curl",
                "tar",
                "where",
                "hostname",
                "whoami",
                "ipconfig",
                "tasklist",
                "findstr",
                "robocopy",
            )
            if (found := shutil.which(name))
        },
    )
