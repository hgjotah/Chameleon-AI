import datetime
import json
import os
import platform
import re
import shutil
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


def build_context(cwd: Path, shell: ShellName, recent: list[str] | None = None) -> Context:
    adapter = WindowsPlatform()
    entries: list[str] = []
    try:
        with os.scandir(cwd) as directory:
            entries = sorted(p.name + ("/" if p.is_dir() else "") for p in islice(directory, 100))
    except OSError:
        entries = []
    return Context(
        shell=shell,
        cwd=str(cwd),
        admin=adapter.is_admin(),
        system_directory=adapter.system_directory(),
        known_directories=adapter.known_directories(),
        entries=entries,
        recent=[redact(s)[:1000] for s in (recent or [])[-6:]],
        executables={
            name: found
            for name in ("git", "python", "winget", "npm", "ssh")
            if (found := shutil.which(name))
        },
    )
