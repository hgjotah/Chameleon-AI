import json
import logging
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QResizeEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from chameleon.core.config import Config, asset_dir
from chameleon.core.intents import refine_request
from chameleon.core.schemas import Plan
from chameleon.platform.windows.shells import describe_action
from chameleon.platform.windows.system import shell_executable
from chameleon.safety.engine import Assessment, Risk
from chameleon.terminal.bridge import Bridge
from chameleon.terminal.session import TerminalSession
from chameleon.ui.widgets import BrandMark, MotionButton, StatusPill


class LocalPage(QWebEnginePage):
    def javaScriptConsoleMessage(
        self,
        level: QWebEnginePage.JavaScriptConsoleMessageLevel,
        message: str,
        line: int,
        source: str,
    ) -> None:
        import logging

        logging.getLogger("chameleon").debug("Renderer line %d: %s", line, message)

    def acceptNavigationRequest(
        self, url: QUrl | str, nav_type: QWebEnginePage.NavigationType, is_main_frame: bool
    ) -> bool:
        url = QUrl(url)
        if url.scheme() in ("file", "qrc"):
            return True
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked and url.scheme() in (
            "http",
            "https",
        ):
            QDesktopServices.openUrl(url)
        return False


class TerminalWindow(QMainWindow):
    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.setWindowTitle("Chameleon Terminal")
        self.resize(1280, 800)
        self.setMinimumSize(720, 440)
        self._windows: list[TerminalWindow] = []
        self._processing_since = 0.0
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(22, 16, 22, 10)
        outer.setSpacing(14)
        header = QHBoxLayout()
        header.setSpacing(14)
        header.addWidget(BrandMark())
        brand = QVBoxLayout()
        title = QLabel("Chameleon")
        title.setStyleSheet("font-size:23px;font-weight:600;color:#f0f6fc")
        subtitle = QLabel("TU TERMINAL. CON INTELIGENCIA LOCAL.")
        subtitle.setObjectName("eyebrow")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()
        self.indicator = StatusPill()
        header.addWidget(self.indicator)
        settings_button = MotionButton("Ajustes")
        settings_button.setToolTip("Personalizar terminal, IA y privacidad · Ctrl+,")
        settings_button.clicked.connect(self.settings)
        header.addWidget(settings_button)
        outer.addLayout(header)
        body_row = QHBoxLayout()
        body_row.setSpacing(18)
        workspace = QFrame()
        workspace.setObjectName("terminalFrame")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(1, 1, 1, 1)
        workspace_layout.setSpacing(0)
        bar = QFrame()
        bar.setObjectName("workspaceBar")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(14, 10, 14, 10)
        shell_button = MotionButton({"cmd": "CMD", "powershell": "PowerShell 5.1", "pwsh": "PowerShell 7"}[config.terminal.shell] + "  ▾")
        shell_button.setToolTip("Abrir una nueva sesión con otro shell")
        menu = QMenu(shell_button)
        for shell, name in (("cmd", "CMD"), ("powershell", "PowerShell 5.1"), ("pwsh", "PowerShell 7")):
            action = menu.addAction(name)
            try:
                shell_executable(shell)
            except OSError:
                action.setEnabled(False)
                action.setText(name + " (no instalado)")
            action.triggered.connect(lambda checked=False, choice=shell: self.new_session(choice))
        shell_button.clicked.connect(lambda: menu.exec(shell_button.mapToGlobal(shell_button.rect().bottomLeft())))
        bar_layout.addWidget(shell_button)
        local_badge = QLabel("LOCAL · PRIVADO")
        local_badge.setObjectName("badge")
        bar_layout.addWidget(local_badge)
        bar_layout.addStretch()
        raw_button = MotionButton("Entrada directa")
        raw_button.setCheckable(True)
        raw_button.setToolTip("Enviar toda la entrada al shell, sin interpretar lenguaje natural")
        self.raw_action = QAction("Entrada directa", self)
        self.raw_action.setCheckable(True)
        raw_button.toggled.connect(self.raw_action.setChecked)
        self.raw_action.toggled.connect(lambda enabled: raw_button.setText("Directa: activa" if enabled else "Entrada directa"))
        bar_layout.addWidget(raw_button)
        guide = MotionButton("Guía")
        guide.clicked.connect(self.show_guide)
        bar_layout.addWidget(guide)
        new_button = MotionButton("+ Nueva sesión", primary=True)
        new_button.clicked.connect(lambda: self.new_session(self.config.terminal.shell))
        bar_layout.addWidget(new_button)
        workspace_layout.addWidget(bar)
        self.view = QWebEngineView(self)
        self.view.setPage(LocalPage(self.view))
        settings = self.view.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False
        )
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
        workspace_layout.addWidget(self.view, 1)
        body_row.addWidget(workspace, 1)
        self.insight_panel = QFrame()
        self.insight_panel.setObjectName("insightPanel")
        self.insight_panel.setFixedWidth(250)
        insight = QVBoxLayout(self.insight_panel)
        insight.setContentsMargins(20, 22, 20, 20)
        insight.setSpacing(15)
        label = QLabel("TU ASISTENTE")
        label.setObjectName("eyebrow")
        insight.addWidget(label)
        title = QLabel("Claridad,\nantes de actuar.")
        title.setStyleSheet("font-size:23px;font-weight:600;color:#eef6f6")
        insight.addWidget(title)
        self.route = QComboBox()
        self.route.addItems(["Automático · rápido", "Qwen · siempre"])
        self.route.setCurrentIndex(1 if config.ai.prefer_model else 0)
        self.route.setToolTip("Automático usa reglas locales cuando son suficientes. Qwen fuerza una llamada real al modelo para las peticiones naturales.")
        self.route.currentIndexChanged.connect(self.change_route)
        insight.addWidget(self.route)
        self.source_label = QLabel("Escribe una petición para ver su origen.")
        self.source_label.setWordWrap(True)
        self.source_label.setObjectName("muted")
        insight.addWidget(self.source_label)
        separator = QFrame()
        separator.setObjectName("divider")
        separator.setFixedHeight(1)
        insight.addWidget(separator)
        self.answer_heading = QLabel("Última petición")
        self.answer_heading.setStyleSheet("font-weight:600;color:#d1ebe2")
        insight.addWidget(self.answer_heading)
        self.answer_label = QLabel("Aquí aparecerá el resultado o la acción propuesta. Los cambios siempre requieren tu confirmación.")
        self.answer_label.setWordWrap(True)
        self.answer_label.setTextFormat(Qt.TextFormat.PlainText)
        self.answer_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.answer_label.setObjectName("muted")
        insight.addWidget(self.answer_label)
        insight.addStretch()
        example = QLabel('Prueba con una frase\n\n«borra el archivo Prueba.txt\nen Downloads»')
        example.setWordWrap(True)
        example.setStyleSheet("color:#8eb3ad;font-size:12px;line-height:1.5")
        insight.addWidget(example)
        help_button = MotionButton("Explorar ejemplos")
        help_button.clicked.connect(self.show_guide)
        insight.addWidget(help_button)
        privacy = QLabel("En tu ordenador.\nTus archivos, bajo tu control.")
        privacy.setObjectName("muted")
        privacy.setStyleSheet("color:#72938f;font-size:11px")
        insight.addWidget(privacy)
        body_row.addWidget(self.insight_panel)
        outer.addLayout(body_row, 1)
        footer = QHBoxLayout()
        self.path_label = QLabel(str(Path(config.terminal.start_directory or Path.home())))
        self.path_label.setObjectName("path")
        self.path_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        footer.addWidget(self.path_label, 1)
        self.activity_label = QLabel("Listo")
        self.activity_label.setObjectName("muted")
        footer.addWidget(self.activity_label)
        keys = QLabel("Ctrl+C cancelar   ·   Ctrl+Shift+V pegar   ·   F11 ampliar")
        keys.setStyleSheet("font-size:11px;color:#7f93ab;margin-left:18px")
        footer.addWidget(keys)
        outer.addLayout(footer)
        self.setCentralWidget(container)
        self.activity_timer = QTimer(self)
        self.activity_timer.setInterval(250)
        self.activity_timer.timeout.connect(lambda: self.activity_label.setText(f"Interpretando · {time.monotonic() - self._processing_since:.1f} s"))
        setting_action = QAction("Ajustes", self)
        setting_action.setShortcut("Ctrl+,")
        setting_action.triggered.connect(self.settings)
        self.addAction(setting_action)
        fullscreen = QAction("Pantalla completa", self)
        fullscreen.setShortcut("F11")
        fullscreen.triggered.connect(
            lambda: self.showNormal() if self.isFullScreen() else self.showFullScreen()
        )
        self.addAction(fullscreen)
        self.session: TerminalSession | None = None
        self.channel = QWebChannel(self.view.page())
        self.view.page().setWebChannel(self.channel)
        self.view.loadFinished.connect(self.loaded)
        # Create the real PTY after the JS channel is initialized, avoiding dropped startup output.
        self.view.setUrl(QUrl.fromLocalFile(str(asset_dir() / "web" / "index.html")))

    def loaded(self, ok: bool) -> None:
        if not ok:
            QMessageBox.critical(self, "Chameleon", "No se pudo cargar el renderer local.")
            return
        self.start_session()

    def start_session(self) -> None:
        if self.session:
            return
        try:
            self.session = TerminalSession(self.config, self)
            self.bridge = Bridge(self.session)
            self.bridge.initialized.connect(self.apply_settings)
            self.channel.registerObject("bridge", self.bridge)
            self.session.plan_ready.connect(self.on_plan)
            self.session.failed.connect(self.on_failure)
            self.session.status.connect(self.on_status)
            self.session.location.connect(self.set_location)
            self.session.exited.connect(lambda: self.on_status("SHELL EXITED"))
            self.raw_action.toggled.connect(lambda raw: setattr(self.session, "raw_mode", raw))
            # Reload once with the registered object; QWebChannel discovers objects at initialization.
            self.view.reload()
            QTimer.singleShot(300, self.apply_settings)
        except Exception as exc:
            QMessageBox.critical(self, "Chameleon", str(exc))

    def apply_settings(self) -> None:
        term = self.config.terminal
        settings = {
            "fontFamily": term.font,
            "fontSize": term.font_size,
            "cursorStyle": term.cursor_style,
            "cursorBlink": term.cursor_blink,
            "scrollback": term.scrollback,
        }
        self.view.page().runJavaScript(
            "if(window.configureTerminal)configureTerminal(" + json.dumps(settings) + ");"
        )

    def on_status(self, status: str) -> None:
        processing = status == "PROCESSING" or status.startswith("QWEN ")
        color = (
            "#81e3bc"
            if status == "AI LOCAL"
            else "#e6c275"
            if processing
            else "#e87979"
            if status == "AI OFFLINE"
            else "#7d9287"
        )
        labels = {"AI LOCAL": "Qwen disponible · local", "PROCESSING": "Preparando tu petición", "AI OFFLINE": "Qwen sin conexión · reglas listas", "AI CHECKING": "Comprobando Qwen", "AI DISABLED": "IA desactivada · reglas listas", "AI ENABLED": "IA activada", "SHELL EXITED": "Sesión terminada"}
        labels.update({"QWEN CONSULTANDO": "Consultando Qwen", "QWEN COMPROBANDO ARCHIVO": "Comprobando datos reales", "QWEN RESPONDIENDO": "Qwen preparando respuesta"})
        self.indicator.set_state(labels.get(status, status), color, processing)
        if processing:
            if not self.activity_timer.isActive():
                self._processing_since = time.monotonic()
            self.activity_timer.start()
        else:
            self.activity_timer.stop()
            self.activity_label.setText("Sesión terminada" if status == "SHELL EXITED" else "Listo")

    def set_location(self, path: str) -> None:
        self.path_label.setToolTip(path)
        self.path_label.setText(self.path_label.fontMetrics().elidedText(path, Qt.TextElideMode.ElideMiddle, max(100, self.path_label.width())))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "insight_panel"):
            self.insight_panel.setVisible(self.width() >= 1080)
        if hasattr(self, "path_label"):
            self.set_location(self.path_label.toolTip() or self.path_label.text())

    def change_route(self, index: int) -> None:
        self.config.ai.prefer_model = index == 1
        if self.session:
            self.session.config.ai.prefer_model = index == 1

    def new_session(self, shell: str) -> None:
        config = self.config.model_copy(deep=True)
        config.terminal.shell = shell  # type: ignore[assignment]
        if self.session:
            config.terminal.start_directory = str(self.session.cwd)
        window = TerminalWindow(config)
        self._windows.append(window)
        window.show()

    def show_guide(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Tu terminal, en tus palabras")
        dialog.resize(600, 440)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Empieza con una frase.")
        title.setObjectName("heading")
        layout.addWidget(title)
        note = QLabel("Escríbela directamente en el terminal. Los comandos habituales\nfuncionan como siempre; los cambios te pedirán confirmación.")
        note.setObjectName("muted")
        layout.addWidget(note)
        examples = QLabel('crea un archivo llamado notas.txt con contenido "Hola"\n\ncrea una carpeta llamada proyecto\n\nve a documentos\n\nlee notas.txt\n\ncopia notas.txt a copia.txt\n\nbusca todos los archivos python mayores de 1 MB')
        examples.setObjectName("path")
        layout.addWidget(examples, 1)
        close = MotionButton("Entendido", primary=True)
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def on_plan(self, plan: Plan, assessment: Assessment) -> None:
        try:
            self._on_plan(plan, assessment)
        except (ValueError, OSError, RuntimeError) as exc:
            self.on_failure(str(exc))
        except Exception as exc:
            logging.getLogger("chameleon").error("Plan dispatch failed: %s", type(exc).__name__)
            self.on_failure("No se pudo preparar la acción. Ejecuta chameleon doctor y vuelve a intentarlo.")

    def _on_plan(self, plan: Plan, assessment: Assessment) -> None:
        if not self.session:
            return
        if self.session.cancel_requested.is_set():
            self.session.reset_prompt()
            return
        self.source_label.setText(plan.trace.label())
        self.answer_heading.setText("Respuesta" if plan.intent == "explain" else "Acción propuesta")
        self.answer_label.setText(plan.summary[:1200])
        if plan.intent == "explain":
            self.session.output.emit("\r\nChameleon: " + plan.summary.replace("\n", "\r\n") + "\r\n")
            self.session.reset_prompt()
            return
        if plan.intent == "clarify":
            if plan.choices:
                answer, ok = QInputDialog.getItem(
                    self, "Chameleon", plan.summary, plan.choices, 0, False
                )
            else:
                answer, ok = QInputDialog.getText(self, "Chameleon", plan.summary)
            self.session.busy = False
            self.session.at_prompt = True
            if ok and answer:
                self.session.submit(refine_request(self.session.last_request, answer, plan))
            else:
                self.session.reset_prompt()
            return
        if plan.intent != "execute" or assessment.level == Risk.BLOCKED:
            self.on_failure(assessment.reason if assessment.level == Risk.BLOCKED else plan.summary)
            return
        if assessment.level == Risk.CONFIRM:
            commands = "\n\n".join(describe_action(a, self.session.cwd, plan.shell != "cmd") for a in plan.actions)
            confirmation = QMessageBox(self)
            confirmation.setWindowTitle("Chameleon necesita confirmación")
            confirmation.setIcon(QMessageBox.Icon.Question)
            confirmation.setTextFormat(Qt.TextFormat.PlainText)
            confirmation.setText("Revisa los cambios antes de continuar.\n\n" + commands + "\n\n" + assessment.reason)
            confirmation.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            confirmation.setDefaultButton(QMessageBox.StandardButton.No)
            choice = confirmation.exec()
            if choice != QMessageBox.StandardButton.Yes:
                self.session.reset_prompt()
                return
        self.session.execute(plan, assessment)

    def on_failure(self, message: str) -> None:
        self.answer_heading.setText("Necesita atención")
        self.answer_label.setText(message)
        if self.session:
            self.session.output.emit("\r\nChameleon: " + message.replace("\n", "\r\n") + "\r\n")
            self.session.reset_prompt()

    def settings(self) -> None:
        from chameleon.setup.settings import SettingsDialog

        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self.config = dialog.config
            if self.session:
                self.session.update_config(self.config)
            self.route.setCurrentIndex(1 if self.config.ai.prefer_model else 0)
            self.apply_settings()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.session:
            self.session.close()
        event.accept()
