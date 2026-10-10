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
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
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
        self.resize(660, 570)
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        title = QLabel("CHAMELEON AI")
        title.setStyleSheet("font-size:30px;color:#51fa8b;font-weight:600;padding:12px")
        layout.addWidget(title)
        layout.addWidget(QLabel("Local AI for your terminal.\nCMD · PowerShell · ConPTY · Ollama"))
        self.ollama = QCheckBox("Instalar Ollama oficial si falta (consentimiento)")
        self.ollama.setChecked(False)
        layout.addWidget(self.ollama)
        self.model = QCheckBox("Descargar modelo local si falta (~2,5 GB) y probar inferencia")
        self.model.setChecked(True)
        layout.addWidget(self.model)
        self.policy = QCheckBox(
            "Permitir RemoteSigned solo para mi usuario si perfiles están bloqueados"
        )
        self.policy.setChecked(False)
        layout.addWidget(self.policy)
        self.desktop = QCheckBox("Crear acceso directo en Desktop")
        layout.addWidget(self.desktop)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        layout.addWidget(self.progress)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        self.buttons: list[QPushButton] = []
        existing = (self.root / "install.json").exists()
        actions = (
            [
                ("Open Chameleon", self.open_terminal),
                ("Repair", self.start_install),
                ("Update", self.start_install),
                ("Uninstall", self.uninstall),
            ]
            if existing
            else [("Install", self.start_install)]
        )
        for name, callback in actions:
            button = QPushButton(name)
            button.clicked.connect(callback)
            self.buttons.append(button)
            layout.addWidget(button)
        settings = QPushButton("Chameleon Settings")
        settings.clicked.connect(self.settings)
        layout.addWidget(settings)
        self.signals.progress.connect(self.log.append)
        self.signals.done.connect(self.finished)
        self.signals.failed.connect(self.failed)
        self.log.append(
            "Instalación por usuario. No requiere Python ni privilegios de administrador.\nLa política de ejecución solo cambia con consentimiento explícito."
        )

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
        self.busy = True
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
        self.log.append(message)
        for button in self.buttons:
            button.setEnabled(True)

    def failed(self, message: str) -> None:
        self.finished("Error: " + message + "\nPuedes volver a ejecutar Repair.")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.busy:
            self.log.append("Espera a que finalice la instalación antes de cerrar Setup.")
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
    if getattr(sys, "frozen", False) and payload is None and "uninstall" not in args:
        current = Path(sys.executable).parent.resolve()
        if current == (data_dir() / "core").resolve():
            temp = Path(tempfile.mkdtemp(prefix="chameleon-repair-"))
            shutil.copytree(current, temp, dirs_exist_ok=True)
            launch(
                [str(temp / "ChameleonSetup.exe"), "--payload", str(temp), "--cleanup", str(temp)],
                creationflags=0x08000000,
            )
            return 0
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
