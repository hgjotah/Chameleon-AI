"""Exercise Qt Setup's worker, real payload copying and local inference in a temp home."""

import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer

from chameleon.platform.windows.installer import install, remove_installation, uninstall_integration
from chameleon.setup import service
from chameleon.setup.app import SetupWindow
from chameleon.terminal.app import create_application

repo = Path(__file__).resolve().parents[1]
evidence = repo / "artifacts"
with tempfile.TemporaryDirectory(prefix="chameleon-setup-qa-") as directory:
    root = Path(directory) / "installed"
    profile = Path(directory) / "existing-profile.ps1"
    original = b"# Existing user profile\r\n"
    profile.write_bytes(original)
    os.environ["CHAMELEON_HOME"] = str(root)

    # Integration APIs are tested separately with an isolated registry hive. This
    # GUI test must never alter the operator's real PATH, shortcuts or profiles.
    def isolated_install(target: Path, payload: Path, *, desktop: bool = False) -> None:
        install(target, payload, profiles=[profile], integrate=False)

    service.install = isolated_install
    service.profile_paths = lambda: []
    app = create_application()
    window = SetupWindow(repo / "dist" / "Chameleon")
    window.model.setChecked(False)
    window.show()
    failed = False

    def finish(message: str, error: bool = False) -> None:
        global failed
        failed = error
        window.busy = False
        window.grab().save(str(evidence / "setup-install.png"))
        (evidence / "setup-install.log").write_text(
            window.log.toPlainText() + "\n" + message, encoding="utf-8"
        )
        window.close()
        app.exit(1 if error else 0)

    window.signals.done.connect(lambda message: finish(message))
    window.signals.failed.connect(lambda message: finish(message, True))
    QTimer.singleShot(200, window.start_install)
    QTimer.singleShot(180000, lambda: finish("Timeout", True))
    code = app.exec()
    if not failed:
        assert (root / "core" / "ChameleonCore.exe").exists()
        assert "Local inference" in window.log.toPlainText()
        uninstall_integration(root, integrate=False)
        assert profile.read_bytes() == original
        remove_installation(root)
        print("PASS: Qt install worker, payload, preserved profile, actual Qwen probe, removal")
    raise SystemExit(code)
