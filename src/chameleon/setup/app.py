import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
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
        self.resize(1100, 820)
        self.setMinimumSize(900, 620)
        body = GlassCanvas()
        self.setCentralWidget(body)
        outer = QHBoxLayout(body)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(30)
        rail = GlassFrame()
        rail.setObjectName("heroCard")
        rail.setFixedWidth(310)
        left = QVBoxLayout(rail)
        left.setContentsMargins(28, 30, 28, 28)
        left.setSpacing(18)
        left.addWidget(BrandMark(size=126))
        brand = QLabel("CHAMELEON AI")
        brand.setObjectName("eyebrow")
        left.addWidget(brand)
        headline = QLabel("Tu terminal.\nAhora habla\ntu idioma.")
        headline.setStyleSheet("font-size:34px;font-weight:600;color:#eef7f4")
        left.addWidget(headline)
        description = QLabel(
            "Un espacio para trabajar con calma.\nQwen en local, acciones claras\ny el control siempre en tus manos."
        )
        description.setObjectName("muted")
        left.addWidget(description)
        left.addSpacing(12)
        self.steps: list[QLabel] = []
        for number, step_title, note in (
            ("01", "Tu espacio de trabajo", "Terminal · CMD · PowerShell"),
            ("02", "Conecta tu IA local", "Ollama · Qwen descargado"),
            ("03", "Comprueba y empieza", "Una llamada real al modelo"),
        ):
            heading = QLabel(number + "  /  " + step_title)
            heading.setObjectName("setupStep")
            self.steps.append(heading)
            left.addWidget(heading)
            label = QLabel(note)
            label.setStyleSheet("font-size:11px;color:#8b9db3")
            left.addWidget(label)
        left.addStretch()
        footer = QLabel("SIN CUENTA · SIN SUSCRIPCIÓN\nInstalación para tu usuario")
        footer.setStyleSheet("font-size:10px;color:#78908a")
        left.addWidget(footer)
        outer.addWidget(rail)
        right = QVBoxLayout()
        right.setSpacing(12)
        eyebrow = QLabel("UN NUEVO ESPACIO PARA HACER MÁS")
        eyebrow.setObjectName("eyebrow")
        right.addWidget(eyebrow)
        existing = (self.root / "install.json").exists()
        title = QLabel("Volvemos a ponerlo a punto." if existing else "Empecemos por aquí.")
        title.setObjectName("heading")
        title.setWordWrap(True)
        right.addWidget(title)
        description = QLabel(
            "Prepara el terminal y comprueba Qwen en pocos pasos.\nTus preferencias y perfiles se conservan al actualizar."
        )
        description.setObjectName("muted")
        right.addWidget(description)
        right.addSpacing(4)
        summary = GlassFrame()
        summary.setObjectName("summaryCard")
        summary_row = QHBoxLayout(summary)
        summary_row.setContentsMargins(18, 15, 18, 15)
        for top, bottom in (
            ("CHAMELEON " + __version__, "Windows · 64 bits"),
            ("100 % LOCAL", "Sin cuenta ni suscripción"),
            ("TÚ DECIDES", "Cambios con confirmación"),
        ):
            column = QVBoxLayout()
            heading = QLabel(top)
            heading.setObjectName("eyebrow")
            caption = QLabel(bottom)
            caption.setObjectName("muted")
            caption.setStyleSheet("font-size:11px;color:#93aba8")
            column.addWidget(heading)
            column.addWidget(caption)
            summary_row.addLayout(column)
        right.addWidget(summary)
        options = GlassFrame()
        options.setObjectName("card")
        choices = QVBoxLayout(options)
        choices.setContentsMargins(18, 14, 18, 14)
        choices.setSpacing(5)
        option_title = QLabel("Personaliza la instalación")
        option_title.setStyleSheet("font-size:16px;font-weight:600;color:#e5efed;margin-bottom:6px")
        choices.addWidget(option_title)
        self.model_choice = QComboBox()
        self.model_choice.addItems(list(MODELS))
        existing_config, _ = load_config(self.root)
        if existing_config.ai.model not in MODELS:
            self.model_choice.addItem(existing_config.ai.model)
        self.model_choice.setCurrentText(existing_config.ai.model)
        choices.addWidget(self.model_choice)
        self.ollama = QCheckBox("Instalar Ollama oficial si falta")
        self.ollama.setToolTip(
            "Solo con tu consentimiento. Descarga de ollama.com con firma verificada."
        )
        self.ollama.setChecked(False)
        choices.addWidget(self.ollama)
        self.model = QCheckBox("Preparar IA: Ollama + Qwen y prueba real")
        self.model.setChecked(True)
        choices.addWidget(self.model)
        size = QLabel(model_description(self.model_choice.currentText()))
        size.setWordWrap(True)
        self.model_choice.currentTextChanged.connect(
            lambda tag: size.setText(model_description(tag))
        )
        size.setObjectName("muted")
        size.setStyleSheet("font-size:11px;color:#8b9eb5")
        choices.addWidget(size)
        self.policy = QCheckBox("Permitir RemoteSigned para mi usuario si hace falta")
        self.policy.setChecked(False)
        self.policy.setToolTip("Requiere confirmación expresa y solo afecta a CurrentUser.")
        choices.addWidget(self.policy)
        self.desktop = QCheckBox("Crear acceso directo en el Escritorio")
        try:
            self.desktop.setChecked(bool(read_manifest(self.root).get("desktop_shortcut")))
        except ValueError:
            pass
        choices.addWidget(self.desktop)
        right.addWidget(options)
        self.dependencies = QLabel("Comprobando componentes instalados…")
        self.dependencies.setWordWrap(True)
        self.dependencies.setObjectName("muted")
        right.addWidget(self.dependencies)
        status_row = QHBoxLayout()
        self.state = StatusPill()
        self.state.set_state("Preparado", "#81e3bc")
        status_row.addWidget(self.state)
        status_row.addStretch()
        right.addLayout(status_row)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress_animation = QPropertyAnimation(self.progress, b"value", self)
        self.progress_animation.setDuration(450)
        self.progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        right.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setStyleSheet(
            "QPlainTextEdit{background:#0b1a20;border:1px solid #274044;border-radius:12px;padding:12px;color:#a0c2bc;font-family:Consolas;font-size:11px}"
        )
        self.log.setMinimumHeight(125)
        right.addWidget(self.log, 1)
        self.buttons: list[QPushButton] = []
        actions = (
            [
                ("Abrir terminal", self.open_terminal),
                ("Reparar", self.start_install),
                ("Actualizar", self.start_install),
                ("Desinstalar", self.uninstall),
            ]
            if existing
            else [("Instalar Chameleon", self.start_install)]
        )
        action_row = QHBoxLayout()
        for index, (name, callback) in enumerate(actions):
            button = MotionButton(name, primary=index == 0)
            button.clicked.connect(callback)
            if index == 0:
                self.primary_button = button
            self.buttons.append(button)
            action_row.addWidget(button)
        right.addLayout(action_row)
        settings = MotionButton("Personalizar ajustes")
        settings.clicked.connect(self.settings)
        self.buttons.append(settings)
        right.addWidget(settings)
        self.signals.progress.connect(self.on_progress)
        self.signals.done.connect(self.finished)
        self.signals.failed.connect(self.failed)
        self.log.appendPlainText(
            "Qwen ocupa ~2,5 GB y se descarga durante la instalación si falta.\nLa IA se marca lista después de una respuesta real de Ollama."
        )
        QTimer.singleShot(0, self.check_dependencies)
        right_body = QWidget()
        # Keep actions visible even when a small screen needs content scrolling.
        right.removeItem(action_row)
        right.removeWidget(settings)
        right_body.setLayout(right)
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(right_body)
        right_pane = QVBoxLayout()
        right_pane.addWidget(scroll, 1)
        right_pane.addLayout(action_row)
        right_pane.addWidget(settings)
        outer.addLayout(right_pane, 1)
        effect = QGraphicsOpacityEffect(rail)
        rail.setGraphicsEffect(effect)
        self.entrance = QPropertyAnimation(effect, b"opacity", self)
        self.entrance.setDuration(480)
        self.entrance.setStartValue(0.2)
        self.entrance.setEndValue(1.0)
        self.entrance.start()
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(1000)
        self.elapsed_timer.timeout.connect(
            lambda: self.state.set_state(
                f"Preparando · {int(time.monotonic() - self.started)} s", "#87e6bc", True
            )
        )

    def on_progress(self, message: str) -> None:
        self.log.appendPlainText(message)
        if message.startswith("COMPONENTES:"):
            self.dependencies.setText(message.removeprefix("COMPONENTES: "))
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
                "font-weight:600;color:" + ("#86e5b9" if index <= phase else "#678c88")
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
        executable = ollama_executable()

        def worker() -> None:
            online, model = asyncio.run(OllamaProvider(config.ai).status())
            self.signals.progress.emit(
                "COMPONENTES: Ollama "
                + ("instalado" if executable else "sin ejecutable local")
                + " · servicio "
                + ("activo" if online else "detenido")
                + " · "
                + config.ai.model
                + (" descargado" if model else " pendiente de comprobar/descargar")
            )

        threading.Thread(target=worker, daemon=True, name="Dependency check").start()

    def open_terminal(self) -> None:
        executable = self.root / "core" / "ChameleonTerminal.exe"
        if executable.exists():
            launch([str(executable)], creationflags=0x08000000)
        else:
            QMessageBox.warning(self, "Chameleon", "Ejecuta Install o Repair primero.")

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
                    "Software externo",
                    "Para preparar la IA falta Ollama. ¿Instalarlo desde ollama.com con firma verificada y preparar el modelo seleccionado si falta?",
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
                    "¿Cambiar CurrentUser a RemoteSigned si es necesario? No se modifica Group Policy.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
        self.progress.setRange(0, 0)
        self.state.set_state("Instalando…", "#81e3bc", True)
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
            "IA pendiente" if "necesita atención" in message else "Instalación completada",
            "#e6c275" if "necesita atención" in message else "#81e3bc",
        )
        for option in (self.ollama, self.model, self.policy, self.desktop):
            option.setEnabled(True)
        for button in self.buttons:
            button.setEnabled(True)
        if (
            self.root / "core/ChameleonTerminal.exe"
        ).is_file() and self.primary_button.text() == "Instalar Chameleon":
            self.primary_button.clicked.disconnect()
            self.primary_button.clicked.connect(self.open_terminal)
            self.primary_button.setText("Abrir mi terminal")

    def failed(self, message: str) -> None:
        self.finished("Error: " + message + "\nPuedes volver a ejecutar Reparar.")
        self.state.set_state("No se completó la instalación", "#ef9797")
        self.progress.setValue(0)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.busy:
            self.log.appendPlainText("Espera a que finalice la instalación antes de cerrar Setup.")
            event.ignore()
        else:
            event.accept()

    def uninstall(self) -> None:
        if (
            QMessageBox.question(
                self,
                "Desinstalar",
                "¿Eliminar Chameleon, su configuración e integración? Se conservarán tus perfiles y otras entradas PATH.",
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
                        "Modelo local",
                        "¿Eliminar también el modelo descargado por Chameleon?",
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
                        "¿Abrir el desinstalador oficial de Ollama? Otros modelos no se eliminarán por Chameleon.",
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
                        "¿Restaurar la política CurrentUser anterior registrada durante Setup?",
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
            QMessageBox.critical(self, "Desinstalación", str(exc))


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
            preparing.state.set_state("Preparando Reparar…", "#81e3bc", True)
            preparing.log.appendPlainText(
                "Preparando una copia temporal para actualizar los archivos en uso. La ventana seguirá respondiendo."
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
                    relocation.done.emit("Preparado")
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
