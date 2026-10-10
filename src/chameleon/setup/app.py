import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chameleon.core.config import data_dir, load_config
from chameleon.platform.windows.installer import (
    read_manifest,
    remove_installation,
    uninstall_integration,
)
from chameleon.platform.windows.system import hidden_run, launch, shell_executable
from chameleon.setup.ollama_install import ollama_executable
from chameleon.setup.service import InstallOptions, SetupService
from chameleon.terminal.app import create_application
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
        self.resize(980, 720)
        self.setMinimumSize(860, 660)
        body = QWidget()
        self.setCentralWidget(body)
        outer = QHBoxLayout(body)
        outer.setContentsMargins(22, 22, 22, 22)
        outer.setSpacing(26)
        rail = QFrame()
        rail.setObjectName("card")
        rail.setFixedWidth(255)
        left = QVBoxLayout(rail)
        left.setContentsMargins(24, 26, 24, 24)
        left.setSpacing(18)
        left.addWidget(BrandMark())
        brand = QLabel("CHAMELEON AI")
        brand.setObjectName("eyebrow")
        left.addWidget(brand)
        headline = QLabel("Todo tu\nterminal.\nEn tus palabras.")
        headline.setStyleSheet("font-size:29px;font-weight:600;color:#eef7ff;line-height:1.2")
        left.addWidget(headline)
        description = QLabel("Inteligencia en tu ordenador.\nArchivos bajo tu control.\nTu shell de siempre.")
        description.setObjectName("muted")
        left.addWidget(description)
        left.addSpacing(12)
        for number, step_title, note in (("01", "Terminal nativo", "CMD y PowerShell"), ("02", "Acciones al instante", "Archivos, carpetas y navegación"), ("03", "IA privada", "Ollama + Qwen en local")):
            heading = QLabel(number + "  /  " + step_title)
            heading.setStyleSheet("font-weight:600;color:#bfe9da")
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
        eyebrow = QLabel("PREPARA TU ESPACIO")
        eyebrow.setObjectName("eyebrow")
        right.addWidget(eyebrow)
        title = QLabel("Listo para empezar.")
        title.setObjectName("heading")
        right.addWidget(title)
        description = QLabel("Instala o repara Chameleon. Conservamos tu configuración\ny el contenido de tus perfiles al actualizar.")
        description.setObjectName("muted")
        right.addWidget(description)
        right.addSpacing(4)
        options = QFrame()
        options.setObjectName("card")
        choices = QVBoxLayout(options)
        choices.setContentsMargins(18, 14, 18, 14)
        choices.setSpacing(5)
        self.ollama = QCheckBox("Instalar Ollama oficial si falta")
        self.ollama.setToolTip("Solo con tu consentimiento. Descarga de ollama.com con firma verificada.")
        self.ollama.setChecked(False)
        choices.addWidget(self.ollama)
        self.model = QCheckBox("Descargar Qwen si falta y comprobar la IA local")
        self.model.setChecked(True)
        choices.addWidget(self.model)
        size = QLabel("     ~2,5 GB · se reutiliza el modelo si ya está instalado")
        size.setObjectName("muted")
        size.setStyleSheet("font-size:11px;color:#8b9eb5")
        choices.addWidget(size)
        self.policy = QCheckBox("Permitir RemoteSigned para mi usuario si hace falta")
        self.policy.setChecked(False)
        self.policy.setToolTip("Requiere confirmación expresa y solo afecta a CurrentUser.")
        choices.addWidget(self.policy)
        self.desktop = QCheckBox("Crear acceso directo en el Escritorio")
        choices.addWidget(self.desktop)
        right.addWidget(options)
        status_row = QHBoxLayout()
        self.state = StatusPill()
        self.state.set_state("Preparado", "#81e3bc")
        status_row.addWidget(self.state)
        status_row.addStretch()
        right.addLayout(status_row)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        right.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setStyleSheet("QPlainTextEdit{background:#0d1520;border:1px solid #28394e;border-radius:10px;padding:10px;color:#a8bbcf;font-family:Consolas;font-size:11px}")
        self.log.setMinimumHeight(125)
        right.addWidget(self.log, 1)
        self.buttons: list[QPushButton] = []
        existing = (self.root / "install.json").exists()
        actions = [("Abrir terminal", self.open_terminal), ("Reparar", self.start_install), ("Actualizar", self.start_install), ("Desinstalar", self.uninstall)] if existing else [("Instalar Chameleon", self.start_install)]
        action_row = QHBoxLayout()
        for index, (name, callback) in enumerate(actions):
            button = MotionButton(name, primary=index == 0)
            button.clicked.connect(callback)
            self.buttons.append(button)
            action_row.addWidget(button)
        right.addLayout(action_row)
        settings = MotionButton("Personalizar ajustes")
        settings.clicked.connect(self.settings)
        self.buttons.append(settings)
        right.addWidget(settings)
        self.signals.progress.connect(self.log.appendPlainText)
        self.signals.done.connect(self.finished)
        self.signals.failed.connect(self.failed)
        self.log.appendPlainText("El terminal y las acciones locales funcionan sin el modelo.\nLa IA se comprueba por separado al terminar la instalación.")
        outer.addLayout(right, 1)

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
        if allow_ollama and not ollama_executable():
            if (
                QMessageBox.question(
                    self,
                    "Software externo",
                    "¿Instalar Ollama desde ollama.com con firma verificada?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
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
                self.signals.done.emit(
                    service.run(InstallOptions(allow_ollama, pull, policy, desktop))
                )
            except Exception as exc:
                self.signals.failed.emit(str(exc))

        threading.Thread(target=worker, daemon=True, name="Setup worker").start()

    def finished(self, message: str) -> None:
        self.busy = False
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.log.appendPlainText(message)
        self.state.set_state("IA pendiente" if "necesita atención" in message else "Instalación completada", "#e6c275" if "necesita atención" in message else "#81e3bc")
        for option in (self.ollama, self.model, self.policy, self.desktop):
            option.setEnabled(True)
        for button in self.buttons:
            button.setEnabled(True)

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
    if getattr(sys, "frozen", False) and payload is None and "uninstall" not in args and "--smoke" not in args:
        current = Path(sys.executable).parent.resolve()
        if current == (data_dir() / "core").resolve():
            temp = Path(tempfile.mkdtemp(prefix="chameleon-repair-"))
            # Show a responsive preparation screen while relocating the DLLs;
            # an installed Qt process cannot replace its own loaded runtime.
            preparing = SetupWindow(current)
            preparing.busy = True
            preparing.progress.setRange(0, 0)
            preparing.state.set_state("Preparando Reparar…", "#81e3bc", True)
            preparing.log.appendPlainText("Preparando una copia temporal para actualizar los archivos en uso. La ventana seguirá respondiendo.")
            for control in (*preparing.buttons, preparing.ollama, preparing.model, preparing.policy, preparing.desktop):
                control.setEnabled(False)
            preparing.show()
            def relocated(message: str) -> None:
                try:
                    launch([str(temp / "ChameleonSetup.exe"), "--payload", str(temp), "--cleanup", str(temp)], creationflags=0x08000000)
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
