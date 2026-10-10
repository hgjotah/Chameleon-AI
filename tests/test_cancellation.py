import asyncio
import os
import time
from pathlib import Path
from types import SimpleNamespace

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


@pytest.mark.gui
@pytest.mark.windows
def test_gui_render_failure_reports_error_and_releases_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from chameleon.core.schemas import Action, Plan
    from chameleon.safety.engine import Assessment, Risk
    from chameleon.terminal.window import TerminalWindow

    monkeypatch.setenv("CHAMELEON_HOME", str(tmp_path))
    _app = QCoreApplication.instance() or QCoreApplication([])
    config = Config()
    config.terminal.start_directory = str(tmp_path)
    terminal = TerminalSession(config)
    terminal.busy = True
    target = tmp_path / "not-written.txt"
    plan = Plan(intent="execute", shell="cmd", summary="Create a large text file",
                actions=[Action(kind="create", path=str(target), content="x" * 9000)])
    failures: list[str] = []
    window = SimpleNamespace(session=terminal)
    window._on_plan = lambda p, a: terminal.execute(p, a)
    window.on_failure = lambda message: (failures.append(message), terminal.reset_prompt())
    try:
        TerminalWindow.on_plan(window, plan, Assessment(Risk.CONFIRM, "Reviewed"))
        assert failures and "CMD" in failures[0]
        assert not terminal.busy and terminal.pending_command is None
        assert not target.exists()
    finally:
        terminal.close()


@pytest.mark.gui
@pytest.mark.windows
def test_settings_shell_applies_only_to_new_sessions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAMELEON_HOME", str(tmp_path))
    app = QCoreApplication.instance() or QCoreApplication([])
    config = Config()
    config.terminal.start_directory = str(tmp_path)
    terminal = TerminalSession(config)
    try:
        updated = config.model_copy(deep=True)
        updated.terminal.shell = "powershell"
        updated.terminal.font_size = 18
        terminal.update_config(updated)
        assert terminal.config.terminal.shell == "cmd"
        assert terminal.config.terminal.font_size == 18
        assert updated.terminal.shell == "powershell"
        app.processEvents()
    finally:
        terminal.close()
