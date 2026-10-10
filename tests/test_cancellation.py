import asyncio
import os
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

from chameleon.core.config import Config
from chameleon.terminal import session as session_module
from chameleon.terminal.session import TerminalSession


@pytest.mark.gui
@pytest.mark.windows
def test_cancel_before_worker_initializes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if os.name != "nt":
        pytest.skip("Real Windows PTY")
    monkeypatch.setenv("CHAMELEON_HOME", str(tmp_path))
    app = QCoreApplication.instance() or QCoreApplication([])
    config = Config()
    config.terminal.start_directory = str(tmp_path)
    terminal = TerminalSession(config)
    failures: list[str] = []
    plans: list[object] = []

    async def slow_plan(self: object, request: str, context: object) -> None:
        await asyncio.sleep(30)

    monkeypatch.setattr(session_module.Engine, "plan", slow_plan)
    terminal.failed.connect(failures.append)
    terminal.plan_ready.connect(lambda plan, assessment: plans.append(plan))
    terminal.at_prompt = True
    try:
        terminal.submit("interpreta esta petición natural")
        terminal.cancel()
        deadline = time.monotonic() + 5
        while not failures and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert failures == ["Cancelado."]
        assert not plans and terminal.pending_command is None
    finally:
        terminal.close()
