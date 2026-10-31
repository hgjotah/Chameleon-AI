"""Explicit diagnostic for the frozen renderer and native PTY, without external tools."""

import json
import secrets
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from chameleon.terminal.window import TerminalWindow


def attach_smoke(app: QApplication, window: TerminalWindow, output: Path, with_ai: bool = False) -> None:
    output.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    stage = 0
    results: list[str] = []
    target: Path | None = None
    confirmations = 0
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
        nonlocal stage, target, confirmations
        if time.monotonic() - start > (120 if with_ai else 30):
            results.append("Timeout stage " + str(stage))
            finish(False)
            return
        session = window.session
        if not session:
            return
        for dialog in app.topLevelWidgets():
            if isinstance(dialog, QMessageBox) and "confirmación" in dialog.windowTitle():
                button = dialog.button(QMessageBox.StandardButton.Yes)
                if button:
                    confirmations += 1
                    button.click()
                return
        if stage == 0 and session.at_prompt:
            results.append("Native ConPTY and local renderer ready")
            target = session.root / ("smoke-" + session.config.terminal.shell + "-" + secrets.token_hex(4) + " Niño")
            target.mkdir(exist_ok=True)
            enter("ve a " + str(target))
            stage = 1
        elif stage == 1 and session.at_prompt and session.cwd == target:
            results.append("Natural request changed real shell cwd")
            enter("echo FROZEN_CHAMELEON_OK")
            stage = 2
        elif stage == 2 and session.at_prompt and "FROZEN_CHAMELEON_OK\r\n" in session.tail:
            results.append("Direct command executed without AI")
            enter('crea un archivo llamado "archivo Niño.txt" con contenido "Hola & echo LITERAL"')
            stage = 4
        elif stage == 4 and confirmations and session.at_prompt and target and (target / "archivo Niño.txt").exists():
            if (target / "archivo Niño.txt").read_text(encoding="utf-8") != "Hola & echo LITERAL":
                results.append("Incorrect literal file content")
                finish(False)
                return
            results.append("Natural creation: confirmation, Unicode path and literal content")
            if with_ai:
                (target / "registro.txt").write_text("El contador real de piezas es 713.", encoding="utf-8")
                session.config.ai.prefer_model=True
                enter("lee el archivo registro.txt")
                stage = 5
                return
            window.resize(1200, 740)
            stage = 3
            QTimer.singleShot(400, lambda: finish(True))
        elif stage == 5 and session.at_prompt and not session.busy and "713" in session.tail and "Ollama" in window.source_label.text():
            results.append("Actual selected model returned a read command only; native file output verified")
            enter("echo AFTER_QWEN_OK")
            stage = 6
        elif stage == 6 and session.at_prompt and "AFTER_QWEN_OK\r\n" in session.tail:
            results.append("Native command after actual model response")
            stage = 3
            QTimer.singleShot(400, lambda: finish(True))

    timer.timeout.connect(tick)
    timer.start(100)
