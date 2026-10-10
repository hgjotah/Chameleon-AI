"""Real Qt/xterm/ConPTY end-to-end smoke, using public terminal APIs."""

import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from chameleon.core.config import Config
from chameleon.core.privacy import configure_logging
from chameleon.terminal.app import create_application
from chameleon.terminal.window import TerminalWindow

root = Path(__file__).resolve().parents[1]
artifacts = root / "artifacts"
artifacts.mkdir(exist_ok=True)
temp = tempfile.TemporaryDirectory(prefix="chameleon-gui-")
os.environ["CHAMELEON_HOME"] = temp.name
configure_logging(Path(temp.name), debug=True)
config = Config()
config.terminal.shell = sys.argv[1] if len(sys.argv) > 1 else "cmd"
config.terminal.start_directory = temp.name
with_ai = "--ai" in sys.argv
if with_ai:
    config.ai.timeout = 180
target = Path(temp.name) / ("Subfolder muy largo con espacios y Niño " * 2).rstrip()
target.mkdir()
if with_ai:
    (target / "large-verified.py").write_bytes(b"#" * 1100000)
    (target / "small-verified.py").write_text("# small", encoding="utf-8")
app = create_application()
window = TerminalWindow(config)
window.show()
start = time.monotonic()
stage = 0
results: list[str] = []
failed = False
accept_creation = False
confirmation_count = 0
creation_file = target / "archivo Niño & 100%.txt"


def tick() -> None:
    global stage, failed, confirmation_count
    session = window.session
    if time.monotonic() - start > (210 if with_ai else 45):
        failed = True
        results.append("FAIL: GUI timeout stage " + str(stage))
        finish()
        return
    if not session:
        return
    for dialog in app.topLevelWidgets():
        if isinstance(dialog, QMessageBox) and "confirmación" in dialog.windowTitle():
            button = dialog.button(QMessageBox.StandardButton.Yes if accept_creation else QMessageBox.StandardButton.No)
            if button:
                confirmation_count += 1
                button.click()
            return
    if stage == 0 and session.at_prompt:
        results.append("PASS: Qt local renderer / ConPTY prompt")
        window.view.page().runJavaScript("feed(" + json.dumps("ve a " + str(target)) + ")")
        stage = 1
        QTimer.singleShot(700, lambda: window.view.page().runJavaScript("feed('\\r')"))
    elif stage == 1 and session.at_prompt and session.cwd == target:
        results.append("PASS: natural input -> local action -> persistent cwd")
        window.view.page().runJavaScript("feed('echo HOLA_CHAMELEON')")
        stage = 2
        QTimer.singleShot(500, lambda: window.view.page().runJavaScript("feed('\\r')"))
    elif stage == 2 and session.at_prompt and "HOLA_CHAMELEON\r\n" in session.tail:
        results.append("PASS: direct shell command, no inference")
        interpreter = Path(sys.executable)
        if interpreter.name.casefold() == "pythonw.exe":
            interpreter = interpreter.with_name("python.exe")
        command = (
            '"' + str(interpreter) + '" -q'
            if config.terminal.shell == "cmd"
            else "& '" + str(interpreter) + "' -q"
        )
        window.view.page().runJavaScript("feed(" + json.dumps(command) + ")")
        stage = 3
        QTimer.singleShot(500, lambda: window.view.page().runJavaScript("feed('\\r')"))
    elif stage == 3 and ">>>" in session.tail and not session.at_prompt:
        results.append("PASS: REPL raw mode")
        window.view.page().runJavaScript(
            "term.write(" + json.dumps("\x1b]0;Chameleon-" + session.token + ";" + str(session.cwd) + "\x07") + ")"
        )
        stage = 10
        QTimer.singleShot(300, verify_replay)
    elif stage == 4 and "REPL_RESULT 323" in session.tail:
        results.append("PASS: REPL input bypasses AI")
        window.view.page().runJavaScript("feed('exit()\\r')")
        stage = 5
    elif stage == 5 and session.at_prompt:
        if with_ai:
            window.view.page().runJavaScript(
                "feed('busca todos los archivos python mayores de 1 MB')"
            )
            stage = 7
            QTimer.singleShot(500, lambda: window.view.page().runJavaScript("feed('\\r')"))
        else:
            start_creation()
    elif stage == 7 and session.at_prompt and "large-verified.py\r\n" in session.tail:
        assert "small-verified.py\r\n" not in session.tail
        results.append("PASS: actual Qwen -> validated filtered query -> native shell output")
        start_creation()

    elif stage == 8 and session.at_prompt and confirmation_count == 1:
        assert not creation_file.exists()
        results.append("PASS: declined file creation leaves filesystem unchanged")
        enter_creation(True)
    elif stage == 9 and session.at_prompt and creation_file.is_file():
        if creation_file.read_text(encoding="utf-8") != "Hola, acci\u00f3n & echo NO_EJECUTAR":
            failed = True
            results.append("FAIL: content mismatch " + ascii(creation_file.read_text(encoding="utf-8")))
            finish()
            return
        results.append("PASS: natural file creation, literal Unicode content, accepted confirmation")
        complete_render()


def verify_replay() -> None:
    global stage, failed
    if window.session and window.session.at_prompt:
        failed = True
        results.append("FAIL: replayed window title enabled AI in REPL")
        finish()
        return
    results.append("PASS: replayed window title leaves REPL in raw mode")
    window.view.page().runJavaScript("feed(\"print('REPL_RESULT', 17*19)\\r\")")
    stage = 4


def start_creation() -> None:
    enter_creation(False)


def enter_creation(accept: bool) -> None:
    global stage, accept_creation
    accept_creation = accept
    stage = 9 if accept else 8
    line = 'crea un archivo llamado "archivo Niño & 100%.txt" con contenido "Hola, acción & echo NO_EJECUTAR"'
    window.view.page().runJavaScript("feed(" + json.dumps(line) + ")")
    QTimer.singleShot(50, lambda: window.view.page().runJavaScript("feed('\\r')"))


def complete_render() -> None:
    global stage
    if window.session:
        window.resize(1230, 760)
        window.view.page().runJavaScript(
            "term.write('\\r\\n\\x1b[38;2;81;250;139mTruecolor · Español: niño, acción\\x1b[0m\\r\\n')"
        )
        stage = 6
        QTimer.singleShot(500, finish)


def finish() -> None:
    timer.stop()
    for log in (Path(temp.name) / "logs").glob("*"):
        print(log.read_text(encoding="utf-8"), flush=True)
    window.grab().save(str(artifacts / ("terminal-" + config.terminal.shell + ".png")))
    (artifacts / ("gui-smoke-" + config.terminal.shell + ".json")).write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print("\n".join(results), flush=True)
    QTimer.singleShot(300, lambda: (window.close(), app.exit(1 if failed else 0)))


timer = QTimer()
timer.timeout.connect(tick)
timer.start(100)
result = app.exec()
logging.shutdown()
temp.cleanup()
raise SystemExit(result)
