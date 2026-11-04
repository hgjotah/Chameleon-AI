"""Run QWidget checks in a fresh process, independent of QCoreApplication tests."""

import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from chameleon.setup.app import SetupWindow
from chameleon.terminal.app import create_application

root = Path(sys.argv[1])
root.mkdir(parents=True, exist_ok=True)
os.environ["CHAMELEON_HOME"] = str(root)
updating = sys.argv[2] == "update"
if updating:
    (root / "install.json").write_text(json.dumps({"version": "0.0.1"}), encoding="utf-8")

calls: list[str] = []
SetupWindow.check_dependencies = lambda self: None  # type: ignore[method-assign]
SetupWindow.start_install = lambda self: calls.append("install")  # type: ignore[method-assign]
SetupWindow.open_terminal = lambda self: calls.append("open")  # type: ignore[method-assign]
app = create_application([])
window = SetupWindow()
window.show()
app.processEvents()
assert not window.ollama.isChecked() and not window.policy.isChecked()
assert not window.log.isVisible() and not window.advanced.isVisible()
assert window.primary_button.text() == ("Update Chameleon" if updating else "Install Chameleon")
QTest.mouseClick(window.primary_button, Qt.MouseButton.LeftButton)
assert calls == ["install"], calls
window.details_toggle.setChecked(True)
assert window.log.isVisible()
window.close()
app.processEvents()
print("PASS: explicit setup action, consent and progressive disclosure")
