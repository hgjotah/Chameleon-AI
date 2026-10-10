"""Explicit, non-installing diagnostic of bundled Setup and Settings resources."""

import json
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from chameleon.core.config import Config
from chameleon.setup.app import SetupWindow
from chameleon.setup.settings import SettingsDialog


def attach_smoke(app: QApplication, window: SetupWindow, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)

    def inspect() -> None:
        window.grab().save(str(output / "frozen-setup.png"))
        settings = SettingsDialog(Config(), window)
        settings.show()
        settings.grab().save(str(output / "frozen-settings.png"))
        ok = len(settings.fields) >= 16 and not window.ollama.isChecked()
        (output / "frozen-setup.json").write_text(
            json.dumps(
                {
                    "ok": ok,
                    "checks": [
                        "Setup loaded",
                        "Settings loaded",
                        "External software consent defaults to off",
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        settings.close()
        window.close()
        app.exit(0 if ok else 1)

    QTimer.singleShot(1500, inspect)
