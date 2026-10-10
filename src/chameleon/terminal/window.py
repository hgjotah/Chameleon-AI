import json

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QInputDialog, QLabel, QMainWindow, QMessageBox, QToolBar

from chameleon.core.config import Config, asset_dir
from chameleon.core.schemas import Plan
from chameleon.platform.windows.shells import CmdAdapter, PowerShellAdapter
from chameleon.safety.engine import Assessment, Risk
from chameleon.terminal.bridge import Bridge
from chameleon.terminal.session import TerminalSession


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
        self.resize(1080, 680)
        self.view = QWebEngineView(self)
        self.view.setPage(LocalPage(self.view))
        settings = self.view.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False
        )
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
        self.setCentralWidget(self.view)
        toolbar = QToolBar("Chameleon", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.addWidget(QLabel("  CHAMELEON TERMINAL  "))
        self.indicator = QLabel("● AI CHECKING")
        toolbar.addWidget(self.indicator)
        setting_action = QAction("Ajustes", self)
        setting_action.triggered.connect(self.settings)
        toolbar.addAction(setting_action)
        self.raw_action = QAction("Raw input", self)
        self.raw_action.setCheckable(True)
        toolbar.addAction(self.raw_action)
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
            self.session.exited.connect(lambda: self.on_status("SHELL EXITED"))
            self.raw_action.toggled.connect(lambda raw: setattr(self.session, "raw_mode", raw))
            # Reload once with the registered object; QWebChannel discovers objects at initialization.
            self.view.reload()
            QTimer.singleShot(300, self.apply_settings)
        except OSError as exc:
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
        self.indicator.setText("● " + status)
        color = (
            "#51fa8b"
            if status == "AI LOCAL"
            else "#e6c275"
            if status == "PROCESSING"
            else "#e87979"
            if status == "AI OFFLINE"
            else "#7d9287"
        )
        self.indicator.setStyleSheet("color:" + color)

    def on_plan(self, plan: Plan, assessment: Assessment) -> None:
        if not self.session:
            return
        if self.session.cancel_requested.is_set():
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
                context = (
                    "elimina "
                    if any(a in plan.summary.casefold() for a in ("eliminar", "delete"))
                    else "ve a "
                )
                self.session.submit(context + answer)
            else:
                self.session.reset_prompt()
            return
        if plan.intent != "execute" or assessment.level == Risk.BLOCKED:
            self.on_failure(assessment.reason if assessment.level == Risk.BLOCKED else plan.summary)
            return
        if assessment.level == Risk.CONFIRM:
            adapter = CmdAdapter() if plan.shell == "cmd" else PowerShellAdapter()
            commands = "\n".join(adapter.render(a, self.session.cwd) for a in plan.actions)
            choice = QMessageBox.question(
                self,
                "Chameleon necesita confirmación",
                plan.summary + "\n\nComando:\n" + commands + "\n\nRiesgo:\n" + assessment.reason,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                self.session.reset_prompt()
                return
        self.session.execute(plan, assessment)

    def on_failure(self, message: str) -> None:
        if self.session:
            self.session.output.emit("\r\nChameleon: " + message.replace("\n", "\r\n") + "\r\n")
            self.session.reset_prompt()

    def settings(self) -> None:
        from chameleon.setup.settings import SettingsDialog

        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self.config = dialog.config
            if self.session:
                self.session.config = self.config
            self.apply_settings()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.session:
            self.session.close()
        event.accept()
