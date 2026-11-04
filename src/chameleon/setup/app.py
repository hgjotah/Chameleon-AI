import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from chameleon import __version__
from chameleon.core.config import data_dir, load_config, save_config
from chameleon.llm.models import MODELS, model_description
from chameleon.platform.windows.installer import (
    read_manifest,
    remove_installation,
    uninstall_integration,
)
from chameleon.platform.windows.system import hidden_run, launch, shell_executable
from chameleon.setup.ollama_install import ollama_executable
from chameleon.setup.service import InstallOptions, SetupService
from chameleon.terminal.app import create_application
from chameleon.ui.glass import GlassCanvas, GlassFrame
from chameleon.ui.motion import motion_enabled
from chameleon.ui.widgets import BrandMark, MotionButton, StatusPill


class WorkerSignals(QObject):
    progress = Signal(str)
    done = Signal(str)
    failed = Signal(str)


class SetupWindow(QMainWindow):
    def __init__(self, payload: Path | None = None) -> None:
        super().__init__()
        self.root = data_dir()
        self.payload = payload
        self.signals = WorkerSignals(self)
        self.busy = False
        self.setWindowTitle("Chameleon Setup")
        self.resize(1080, 760)
        self.setMinimumSize(840, 600)
        body = GlassCanvas()
        self.setCentralWidget(body)
        outer = QHBoxLayout(body)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(30)
        rail = QFrame()
        rail.setObjectName("heroCard")
        rail.setFixedWidth(276)
        left = QVBoxLayout(rail)
        left.setContentsMargins(24, 28, 24, 24)
        left.setSpacing(14)
        left.addWidget(BrandMark(size=56))
        brand = QLabel("CHAMELEON")
        brand.setObjectName("eyebrow")
        left.addWidget(brand)
        left.addSpacing(15)
        headline = QLabel("It starts\non your device.")
        headline.setStyleSheet("font-size:31px;font-weight:600;color:#edf3e7")
        left.addWidget(headline)
        description = QLabel("A terminal with local AI.\nYou stay in control.")
        description.setObjectName("muted")
        left.addWidget(description)
        left.addStretch()
        self.steps: list[QLabel] = []
        for number, step_title, step_note in (
            ("01", "Your terminal", "CMD and PowerShell"),
            ("02", "Your local AI", "Ollama and your chosen model"),
            ("03", "All set", "Connection verified"),
        ):
            step = QLabel(number + "   " + step_title)
            step.setObjectName("setupStep")
            self.steps.append(step)
            left.addWidget(step)
            caption = QLabel(step_note)
            caption.setStyleSheet("font-size:11px;color:#829c85;margin-left:28px")
            left.addWidget(caption)
        left.addSpacing(18)
        version = QLabel("Windows · 64 bits     /     " + __version__)
        version.setStyleSheet("color:#7f9981;font-size:10px")
        left.addWidget(version)
        outer.addWidget(rail)
        existing = (self.root / "install.json").exists()
        try:
            previous = read_manifest(self.root) if existing else {}
        except (OSError, ValueError):
            previous = {}
        needs_update = existing and previous.get("version") != __version__
        right_body = QWidget()
        right = QVBoxLayout(right_body)
        right.setContentsMargins(1, 9, 9, 8)
        right.setSpacing(14)
        eyebrow = QLabel("LOCAL INSTALLATION")
        eyebrow.setObjectName("eyebrow")
        right.addWidget(eyebrow)
        title = QLabel("Your workspace, up to date." if existing else "Set up your workspace.")
        title.setObjectName("heading")
        right.addWidget(title)
        description = QLabel("Your terminal and AI, ready to work. Your preferences are preserved.")
        description.setWordWrap(True)
        description.setObjectName("muted")
        right.addWidget(description)
        right.addSpacing(9)
        options = QFrame()
        options.setObjectName("card")
        choices = QVBoxLayout(options)
        choices.setContentsMargins(20, 18, 20, 18)
        choices.setSpacing(8)
        label = QLabel("Local model")
        label.setStyleSheet("font-weight:600;color:#d8e7d4")
        choices.addWidget(label)
        self.model_choice = QComboBox()
        self.model_choice.addItems(list(MODELS))
        config, _ = load_config(self.root)
        if config.ai.model not in MODELS:
            self.model_choice.addItem(config.ai.model)
        self.model_choice.setCurrentText(config.ai.model)
        choices.addWidget(self.model_choice)
        size = QLabel(model_description(self.model_choice.currentText()))
        size.setWordWrap(True)
        size.setObjectName("muted")
        size.setStyleSheet("font-size:11px;color:#93ac93;margin-bottom:8px")
        self.model_choice.currentTextChanged.connect(
            lambda tag: size.setText(model_description(tag))
        )
        choices.addWidget(size)
        self.model = QCheckBox("Prepare AI and verify the connection")
        self.model.setChecked(True)
        choices.addWidget(self.model)
        self.ollama = QCheckBox("Allow official Ollama installation if missing")
        self.ollama.setChecked(False)
        self.ollama.setToolTip(
            "Downloads from ollama.com with a verified signature. Requires your consent."
        )
        choices.addWidget(self.ollama)
        self.desktop = QCheckBox("Create a desktop shortcut")
        self.desktop.setChecked(bool(previous.get("desktop_shortcut")))
        choices.addWidget(self.desktop)
        right.addWidget(options)
        advanced_button = MotionButton("Advanced options  +")
        advanced_button.setFlat(True)
        advanced_button.setCheckable(True)
        right.addWidget(advanced_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.advanced = QWidget()
        advanced_layout = QVBoxLayout(self.advanced)
        advanced_layout.setContentsMargins(10, 0, 0, 0)
        self.policy = QCheckBox("Allow RemoteSigned for my user if needed")
        self.policy.setChecked(False)
        self.policy.setToolTip(
            "CurrentUser only, with explicit confirmation. Does not change Group Policy."
        )
        advanced_layout.addWidget(self.policy)
        self.advanced.hide()
        right.addWidget(self.advanced)
        advanced_button.toggled.connect(self.advanced.setVisible)
        advanced_button.toggled.connect(
            lambda opened: advanced_button.setText(
                "Advanced options  −" if opened else "Advanced options  +"
            )
        )
        self.dependencies = QLabel("Checking components…")
        self.dependencies.setWordWrap(True)
        self.dependencies.setObjectName("muted")
        self.dependencies.setStyleSheet("font-size:11px;color:#92a992")
        right.addWidget(self.dependencies)
        self.state = StatusPill()
        self.state.set_state("Ready", "#b7d59b")
        state_row = QHBoxLayout()
        state_row.addWidget(self.state)
        state_row.addStretch()
        right.addLayout(state_row)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress_animation = QPropertyAnimation(self.progress, b"value", self)
        self.progress_animation.setDuration(350 if motion_enabled() else 0)
        self.progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        right.addWidget(self.progress)
        self.details_toggle = MotionButton("Show details  +")
        self.details_toggle.setFlat(True)
        self.details_toggle.setCheckable(True)
        right.addWidget(self.details_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setMaximumHeight(170)
        self.log.setStyleSheet(
            "QPlainTextEdit{background:#0d1710;border:1px solid #304634;border-radius:10px;padding:12px;color:#a4bca0;font-family:Consolas;font-size:11px}"
        )
        self.log.hide()
        right.addWidget(self.log)
        self.details_toggle.toggled.connect(self.log.setVisible)
        self.details_toggle.toggled.connect(
            lambda opened: self.details_toggle.setText(
                "Hide details  −" if opened else "Show details  +"
            )
        )
        self.log.appendPlainText(
            "Setup verifies the terminal, Ollama and a real response from the selected model."
        )
        right.addStretch()
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(right_body)
        right_pane = QVBoxLayout()
        right_pane.setSpacing(14)
        right_pane.addWidget(scroll, 1)
        dock = GlassFrame()
        action_row = QHBoxLayout(dock)
        action_row.setContentsMargins(12, 12, 12, 12)
        action_row.setSpacing(8)
        if not existing:
            scope_note = QLabel("Local installation")
            scope_note.setStyleSheet("color:#a0b59a;font-size:11px;margin-left:9px")
            action_row.addWidget(scope_note)
        action_row.addStretch()
        self.buttons: list[QPushButton] = []
        primary_text = (
            "Update Chameleon"
            if needs_update
            else "Open terminal"
            if existing
            else "Install Chameleon"
        )
        self.primary_button = MotionButton(primary_text, primary=True)
        self.primary_button.setMinimumWidth(210)
        self.primary_button.clicked.connect(
            self.start_install if needs_update or not existing else self.open_terminal
        )
        self.buttons.append(self.primary_button)
        action_row.addWidget(self.primary_button)
        if existing:
            repair = MotionButton("Open terminal" if needs_update else "Repair")
            repair.clicked.connect(self.open_terminal if needs_update else self.start_install)
            self.buttons.append(repair)
            action_row.addWidget(repair)
        more = MotionButton("···")
        more.setFixedWidth(46)
        more.setAccessibleName("More options")
        menu = QMenu(more)
        menu.addAction("Settings", self.settings)
        if existing:
            menu.addAction("Repair installation", self.start_install)
            menu.addSeparator()
            menu.addAction("Uninstall…", self.uninstall)
        more.clicked.connect(lambda: menu.exec(more.mapToGlobal(more.rect().topLeft())))
        action_row.addWidget(more)
        self.buttons.append(more)
        right_pane.addWidget(dock)
        note = QLabel("No account. No subscription. On your device.")
        note.setStyleSheet("color:#7f9980;font-size:10px;padding-left:8px")
        right_pane.addWidget(note)
        outer.addLayout(right_pane, 1)
        self.signals.progress.connect(self.on_progress)
        self.signals.done.connect(self.finished)
        self.signals.failed.connect(self.failed)
        QTimer.singleShot(0, self.check_dependencies)
        self.model_choice.currentTextChanged.connect(lambda _: self.check_dependencies())
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(1000)
        self.elapsed_timer.timeout.connect(
            lambda: self.state.set_state(
                f"Preparing · {int(time.monotonic() - self.started)} s", "#b8d79e", True
            )
        )

    def on_progress(self, message: str) -> None:
        self.log.appendPlainText(message)
        if message.startswith("COMPONENTS:"):
            self.dependencies.setText(message.removeprefix("COMPONENTS: "))
            return
        phase = (
            2
            if any(word in message for word in ("inferencia", "inference", "Qwen"))
            else 1
            if any(word in message for word in ("Ollama", "download", "descarg"))
            else 0
        )
        for index, heading in enumerate(self.steps):
            heading.setStyleSheet(
                "font-weight:600;color:" + ("#b1cf98" if index <= phase else "#738b75")
            )
        if self.busy:
            import re

            percent = re.search(r"(\d+)%", message)
            self.progress_animation.stop()
            self.progress.setRange(0, 100 if percent else 0)
            if percent:
                self.progress.setValue(min(100, int(percent[1])))

    def check_dependencies(self) -> None:
        import asyncio

        from chameleon.llm.ollama import OllamaProvider

        config, _ = load_config(self.root)
        config.ai.model = self.model_choice.currentText()
        executable = ollama_executable()
        self._dependency_revision = getattr(self, "_dependency_revision", 0) + 1
        revision = self._dependency_revision

        def worker() -> None:
            online, model = asyncio.run(OllamaProvider(config.ai).status())
            if revision != self._dependency_revision:
                return
            self.signals.progress.emit(
                "COMPONENTS: Ollama "
                + ("installed" if executable else "no local executable")
                + " · service "
                + ("active" if online else "stopped")
                + " · "
                + config.ai.model
                + (" downloaded" if model else " awaiting verification/download")
            )

        threading.Thread(target=worker, daemon=True, name="Dependency check").start()

    def open_terminal(self) -> None:
        executable = self.root / "core" / "ChameleonTerminal.exe"
        if executable.exists():
            launch([str(executable)], creationflags=0x08000000)
        else:
            QMessageBox.warning(self, "Chameleon", "Run Install or Repair first.")

    def settings(self) -> None:
        from chameleon.setup.settings import SettingsDialog

        config, _ = load_config()
        SettingsDialog(config, self).exec()

    def start_install(self) -> None:
        allow_ollama, pull, policy, desktop = (
            self.ollama.isChecked(),
            self.model.isChecked(),
            self.policy.isChecked(),
            self.desktop.isChecked(),
        )
        selected_model = self.model_choice.currentText()
        if (allow_ollama or pull) and not ollama_executable():
            if (
                QMessageBox.question(
                    self,
                    "External software",
                    "Ollama is required to prepare AI. Install it from ollama.com with a verified signature and prepare the selected model if missing?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
            allow_ollama = True
        if policy:
            if (
                QMessageBox.question(
                    self,
                    "Execution Policy",
                    "Change CurrentUser to RemoteSigned if needed? Group Policy will not be changed.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
        self.progress.setRange(0, 0)
        self.state.set_state("Installing…", "#b5d498", True)
        self.busy = True
        self.model_choice.setEnabled(False)
        self.started = time.monotonic()
        self.elapsed_timer.start()
        for option in (self.ollama, self.model, self.policy, self.desktop):
            option.setEnabled(False)
        for button in self.buttons:
            button.setEnabled(False)

        def worker() -> None:
            try:
                payload = self.payload or Path(sys.executable).parent
                if not (payload / "ChameleonCore.exe").exists():
                    payload = Path.cwd() / "dist" / "Chameleon"
                service = SetupService(self.root, payload, self.signals.progress.emit)
                selected_config, _ = load_config(self.root)
                selected_config.ai.model = selected_model
                save_config(selected_config, self.root)
                self.signals.done.emit(
                    service.run(InstallOptions(allow_ollama, pull, policy, desktop))
                )
            except Exception as exc:
                self.signals.failed.emit(str(exc))

        threading.Thread(target=worker, daemon=True, name="Setup worker").start()

    def finished(self, message: str) -> None:
        self.busy = False
        self.model_choice.setEnabled(True)
        self.elapsed_timer.stop()
        self.progress_animation.stop()
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.log.appendPlainText(message)
        self.check_dependencies()
        self.state.set_state(
            "AI pending" if "needs attention" in message else "Installation complete",
            "#e6c275" if "needs attention" in message else "#b5d498",
        )
        for option in (self.ollama, self.model, self.policy, self.desktop):
            option.setEnabled(True)
        for button in self.buttons:
            button.setEnabled(True)
        if (self.root / "core/ChameleonTerminal.exe").is_file() and self.primary_button.text() in (
            "Install Chameleon",
            "Update Chameleon",
        ):
            self.primary_button.clicked.disconnect()
            self.primary_button.clicked.connect(self.open_terminal)
            self.primary_button.setText("Open my terminal")

    def failed(self, message: str) -> None:
        self.finished("Error: " + message + "\nYou can run Repair again.")
        self.state.set_state("Installation did not finish", "#ef9797")
        self.details_toggle.setChecked(True)
        self.progress.setValue(0)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.busy:
            self.log.appendPlainText("Wait for installation to finish before closing Setup.")
            event.ignore()
        else:
            event.accept()

    def uninstall(self) -> None:
        if (
            QMessageBox.question(
                self,
                "Uninstall",
                "Remove Chameleon, its configuration and shell integration? Your profiles and other PATH entries will be preserved.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            config, _ = load_config()
            manifest = read_manifest(self.root)
            if manifest.get("downloaded_model"):
                if (
                    QMessageBox.question(
                        self,
                        "Local model",
                        "Also remove the model downloaded by Chameleon?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    == QMessageBox.StandardButton.Yes
                ):
                    executable = ollama_executable()
                    if executable:
                        hidden_run([executable, "rm", manifest["downloaded_model"]], timeout=60)
            if manifest.get("installed_ollama"):
                if (
                    QMessageBox.question(
                        self,
                        "Ollama",
                        "Open the official Ollama uninstaller? Chameleon will not remove other models.",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    == QMessageBox.StandardButton.Yes
                ):
                    uninstaller = (
                        Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Ollama" / "unins000.exe"
                    )
                    if uninstaller.exists():
                        launch([str(uninstaller)])
            if manifest.get("policy_before"):
                if (
                    QMessageBox.question(
                        self,
                        "Execution Policy",
                        "Restore the previous CurrentUser policy recorded during Setup?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    == QMessageBox.StandardButton.Yes
                ):
                    for shell, value in manifest["policy_before"].items():
                        if value in (
                            "Undefined",
                            "Restricted",
                            "RemoteSigned",
                            "AllSigned",
                            "Unrestricted",
                            "Bypass",
                        ):
                            hidden_run(
                                [
                                    shell_executable(shell),
                                    "-NoProfile",
                                    "-Command",
                                    f"Set-ExecutionPolicy -Scope CurrentUser {value} -Force",
                                ],
                                timeout=15,
                            )
            uninstall_integration(self.root)
            remove_installation(self.root, delayed=True)
            self.close()
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Uninstall", str(exc))


def main(argv: list[str] | None = None) -> int:
    app = create_application(argv)
    args = argv or sys.argv[1:]
    if "settings" in args:
        from chameleon.setup.settings import SettingsDialog

        config, _ = load_config()
        dialog = SettingsDialog(config)
        dialog.show()
        return app.exec()
    payload = Path(args[args.index("--payload") + 1]) if "--payload" in args else None
    if (
        getattr(sys, "frozen", False)
        and payload is None
        and "uninstall" not in args
        and "--smoke" not in args
    ):
        current = Path(sys.executable).parent.resolve()
        if current == (data_dir() / "core").resolve():
            temp = Path(tempfile.mkdtemp(prefix="chameleon-repair-"))
            # Show a responsive preparation screen while relocating the DLLs;
            # an installed Qt process cannot replace its own loaded runtime.
            preparing = SetupWindow(current)
            preparing.busy = True
            preparing.progress.setRange(0, 0)
            preparing.state.set_state("Preparing Repair…", "#b5d498", True)
            preparing.log.appendPlainText(
                "Preparing a temporary copy to update files in use. The window will remain responsive."
            )
            for control in (
                *preparing.buttons,
                preparing.ollama,
                preparing.model,
                preparing.policy,
                preparing.desktop,
            ):
                control.setEnabled(False)
            preparing.show()

            def relocated(message: str) -> None:
                try:
                    launch(
                        [
                            str(temp / "ChameleonSetup.exe"),
                            "--payload",
                            str(temp),
                            "--cleanup",
                            str(temp),
                        ],
                        creationflags=0x08000000,
                    )
                    preparing.busy = False
                    preparing.close()
                    app.quit()
                except OSError as exc:
                    preparing.failed(str(exc))

            relocation = WorkerSignals(preparing)
            relocation.done.connect(relocated)
            relocation.failed.connect(preparing.failed)

            def copy_runtime() -> None:
                try:
                    shutil.copytree(current, temp, dirs_exist_ok=True)
                    relocation.done.emit("Ready")
                except OSError as exc:
                    relocation.failed.emit(str(exc))

            threading.Thread(target=copy_runtime, daemon=True, name="Repair preparation").start()
            return app.exec()
    window = SetupWindow(payload)
    window.show()
    if "--smoke" in args:
        from chameleon.setup.smoke import attach_smoke

        attach_smoke(app, window, Path(args[args.index("--smoke") + 1]))
    if "uninstall" in args:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(100, window.uninstall)
    result = app.exec()
    if "--cleanup" in args:
        temp = Path(args[args.index("--cleanup") + 1]).resolve()
        temp_base = Path(tempfile.gettempdir()).resolve()
        if (
            temp.parent == temp_base
            and temp.name.startswith("chameleon-repair-")
            and Path(sys.executable).resolve().is_relative_to(temp)
        ):
            from chameleon.platform.windows.shells import ps_quote

            script = (
                "Start-Sleep -Seconds 3; Remove-Item -LiteralPath "
                + ps_quote(str(temp))
                + " -Recurse -Force"
            )
            launch(
                [shell_executable("powershell"), "-NoProfile", "-Command", script],
                creationflags=0x08000000,
            )
    return result
