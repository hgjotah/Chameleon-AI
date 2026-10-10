import json
import os
import tempfile
import time
from pathlib import Path

import psutil

from chameleon.core.privacy import redact


def shell_identity(pid: int | None = None) -> tuple[int, float]:
    process = psutil.Process(pid) if pid else psutil.Process(os.getpid())
    if pid is None:
        ancestors = process.parents()
        shells = [
            p for p in ancestors if p.name().casefold() in ("cmd.exe", "powershell.exe", "pwsh.exe")
        ]
        if shells:
            process = shells[0]
    return process.pid, process.create_time()


class SessionStore:
    def __init__(self, root: Path, pid: int | None = None) -> None:
        self.directory = root / "runtime" / "sessions"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.pid, self.created = shell_identity(pid)
        self.path = self.directory / f"{self.pid}.json"
        self.cleanup()

    def cleanup(self) -> None:
        for path in self.directory.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                alive = psutil.Process(int(path.stem)).create_time() == data["created"]
                if not alive or time.time() - data["updated"] > 1800:
                    path.unlink(missing_ok=True)
            except (OSError, ValueError, KeyError, psutil.Error):
                path.unlink(missing_ok=True)

    def recent(self) -> list[str]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data["created"] == self.created and time.time() - data["updated"] < 1800:
                return list(data["recent"])[-6:]
        except (OSError, ValueError, KeyError):
            return []
        return []

    def remember(self, text: str) -> None:
        recent = (self.recent() + [redact(text)[:1000]])[-6:]
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=self.directory,
            prefix=f"{self.pid}-",
            suffix=".tmp",
            encoding="utf-8",
            delete=False,
        ) as stream:
            json.dump(
                {"created": self.created, "updated": time.time(), "recent": recent},
                stream,
                ensure_ascii=False,
            )
            temp = Path(stream.name)
        temp.replace(self.path)
