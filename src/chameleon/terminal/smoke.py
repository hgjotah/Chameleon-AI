"""Explicit diagnostic for the frozen renderer and native PTY, without external tools."""

import json
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from chameleon.terminal.window import TerminalWindow


def attach_smoke(app: QApplication, window: TerminalWindow, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    stage = 0
    results: list[str] = []
    target: Path | None = None
    timer = QTimer(window)

    def enter(line: str) -> None:
        window.view.page().runJavaScript("feed(" + json.dumps(line) + ")")
        QTimer.singleShot(600, lambda: window.view.page().runJavaScript("feed('\\r')"))

    def finish(ok: bool) -> None:
        timer.stop()
        window.grab().save(str(output / "frozen-terminal.png"))
        (output / "frozen-terminal.json").write_text(
            json.dumps({"ok": ok, "checks": results}, indent=2), encoding="utf-8"
        )
        QTimer.singleShot(200, lambda: (window.close(), app.exit(0 if ok else 1)))

    def tick() -> None:
        nonlocal stage, target
        if time.monotonic() - start > 30:
            results.append("Timeout stage " + str(stage))
            finish(False)
            return
        session = window.session
        if not session:
            return
        if stage == 0 and session.at_prompt:
            results.append("Native ConPTY and local renderer ready")
            target = session.root / "smoke-folder Niño"
            target.mkdir(exist_ok=True)
            enter("ve a " + str(target))
            stage = 1
        elif stage == 1 and session.at_prompt and session.cwd == target:
            results.append("Natural request changed real shell cwd")
            enter("echo FROZEN_CHAMELEON_OK")
            stage = 2
        elif stage == 2 and session.at_prompt and "FROZEN_CHAMELEON_OK\r\n" in session.tail:
            results.append("Direct command executed without AI")
            window.resize(1200, 740)
            stage = 3
            QTimer.singleShot(400, lambda: finish(True))

    timer.timeout.connect(tick)
    timer.start(100)
