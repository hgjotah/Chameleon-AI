import json
import logging
import time
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
    QUrl,
)
from PySide6.QtGui import QAction, QCloseEvent, QColor, QDesktopServices, QResizeEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
)

from chameleon.core.config import Config, asset_dir
from chameleon.core.intents import refine_request
from chameleon.core.schemas import Plan
from chameleon.llm.models import MODELS
from chameleon.platform.windows.shells import describe_action
from chameleon.platform.windows.system import shell_executable
from chameleon.safety.engine import Assessment, Risk
from chameleon.terminal.bridge import Bridge
from chameleon.terminal.session import TerminalSession
from chameleon.ui.glass import GlassCanvas, GlassFrame
from chameleon.ui.motion import motion_enabled
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
        container = GlassCanvas()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(22, 16, 22, 10)
        outer.setSpacing(14)
        header = QHBoxLayout()
        header.setSpacing(14)
        header.addWidget(BrandMark(size=36))
        brand = QVBoxLayout()
        title = QLabel("Chameleon")
        title.setStyleSheet("font-size:20px;font-weight:600;color:#edf3e9")
        subtitle = QLabel("TERMINAL")
        subtitle.setObjectName("eyebrow")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()
        self.indicator = StatusPill()
        settings_button = MotionButton("Settings")
        settings_button.setToolTip("Customize terminal, AI and privacy · Ctrl+,")
        settings_button.clicked.connect(self.settings)
        header.addWidget(settings_button)
        outer.addLayout(header)
        body_row = QHBoxLayout()
        body_row.setSpacing(18)
        workspace = QFrame()
        self.workspace = workspace
        workspace.setObjectName("terminalFrame")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(8, 8, 8, 8)
        workspace_layout.setSpacing(0)
        bar = GlassFrame()
        bar.setObjectName("commandDock")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(14, 10, 14, 10)
        shell_button = MotionButton(
            {"cmd": "CMD", "powershell": "PowerShell 5.1", "pwsh": "PowerShell 7"}[
                config.terminal.shell
            ]
            + "  ▾"
        )
        shell_button.setToolTip("Open a new session with another shell")
        menu = QMenu(shell_button)
        for shell, name in (
            ("cmd", "CMD"),
            ("powershell", "PowerShell 5.1"),
            ("pwsh", "PowerShell 7"),
        ):
            action = menu.addAction(name)
            try:
                shell_executable(shell)
            except OSError:
                action.setEnabled(False)
                action.setText(name + " (not installed)")
            action.triggered.connect(lambda checked=False, choice=shell: self.new_session(choice))
        shell_button.clicked.connect(
            lambda: menu.exec(shell_button.mapToGlobal(shell_button.rect().bottomLeft()))
        )
        bar_layout.addWidget(shell_button)
        local_badge = QLabel("LOCAL · PRIVADO")
        local_badge.setObjectName("badge")
        local_badge.hide()
        bar_layout.addStretch()
        bar_layout.addWidget(self.indicator)
        raw_button = MotionButton("Direct input")
        raw_button.setCheckable(True)
        raw_button.setToolTip("Send all input to the shell without interpreting natural language")
        self.raw_action = QAction("Direct input", self)
        self.raw_action.setCheckable(True)
        raw_button.toggled.connect(self.raw_action.setChecked)
        self.raw_action.toggled.connect(raw_button.setChecked)
        self.raw_action.toggled.connect(
            lambda enabled: raw_button.setText("Direct input: on" if enabled else "Direct input")
        )
        raw_button.setFlat(True)
        guide = MotionButton("Guide")
        guide.clicked.connect(self.show_guide)
        header.insertWidget(header.count() - 1, guide)
        guide.setFlat(True)
        self.drawer_button = MotionButton("AI and permissions")
        self.drawer_button.setFixedWidth(150)
        self.drawer_button.setCheckable(True)
        self.drawer_button.toggled.connect(self.toggle_insights)
        self.drawer_button.setToolTip("Model, permissions and request details")
        bar_layout.addWidget(self.drawer_button)
        new_button = MotionButton("+")
        new_button.setFixedWidth(44)
        new_button.setToolTip("New session")
        new_button.setAccessibleName("New session")
        new_button.clicked.connect(lambda: self.new_session(self.config.terminal.shell))
        bar_layout.addWidget(new_button)
        outer.addWidget(bar)
        self.view = QWebEngineView(self)
        self.view.setPage(LocalPage(self.view))
        self.view.page().setBackgroundColor(QColor("#0b100d"))
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
        self.insight_panel.setMinimumWidth(290)
        insight = QVBoxLayout(self.insight_panel)
        insight.setContentsMargins(20, 22, 20, 20)
        insight.setSpacing(15)
        label = QLabel("SESSION SETTINGS")
        label.setObjectName("eyebrow")
        insight.addWidget(label)
        title = QLabel("AI and permissions")
        title.setStyleSheet("font-size:21px;font-weight:600;color:#edf3e9")
        insight.addWidget(title)
        self.model_picker = QComboBox()
        self.model_picker.addItems(list(MODELS))
        if config.ai.model not in MODELS:
            self.model_picker.addItem(config.ai.model)
        self.model_picker.setCurrentText(config.ai.model)
        self.model_picker.currentTextChanged.connect(self.change_model)
        model_label = QLabel("Local model")
        model_label.setObjectName("muted")
        insight.addWidget(model_label)
        insight.addWidget(self.model_picker)
        self.access_picker = QComboBox()
        for mode, mode_label in (
            ("read_only", "Read only"),
            ("balanced", "Balanced"),
            ("developer", "Developer · confirm"),
            ("custom", "Custom"),
            ("full", "Full access · no confirmation"),
        ):
            self.access_picker.addItem(mode_label, mode)
        self.access_picker.setCurrentIndex(self.access_picker.findData(config.safety.mode))
        self.access_picker.currentIndexChanged.connect(self.change_access)
        self.access_picker.setToolTip(
            "Permissions for this window. Customize and save in Settings → Model access."
        )
        access_label = QLabel("Model access")
        access_label.setObjectName("muted")
        insight.addWidget(access_label)
        insight.addWidget(self.access_picker)
        self.route = QComboBox()
        self.route.addItems(["Automatic · fast", "Qwen · always"])
        self.route.setCurrentIndex(1 if config.ai.prefer_model else 0)
        self.route.setToolTip(
            "Automatic uses local rules when sufficient. Qwen forces a real model call for natural-language requests."
        )
        self.route.currentIndexChanged.connect(self.change_route)
        insight.addWidget(self.route)
        insight.addWidget(raw_button)
        self.source_label = QLabel("Enter a request to see its source.")
        self.source_label.setWordWrap(True)
        self.source_label.setObjectName("muted")
        insight.addWidget(self.source_label)
        separator = QFrame()
        separator.setObjectName("divider")
        separator.setFixedHeight(1)
        insight.addWidget(separator)
        self.answer_heading = QLabel("Last request")
        self.answer_heading.setStyleSheet("font-weight:600;color:#d1ebe2")
        insight.addWidget(self.answer_heading)
        self.answer_label = QLabel(
            "Only the command will appear here. You choose permissions and confirmations."
        )
        self.answer_label.setWordWrap(True)
        self.answer_label.setTextFormat(Qt.TextFormat.PlainText)
        self.answer_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.answer_label.setObjectName("muted")
        self.answer_label.setMaximumHeight(150)
        insight.addWidget(self.answer_label)
        insight.addStretch()
        self.insight_scroll = QScrollArea(container)
        self.insight_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.insight_scroll.setWidgetResizable(True)
        self.insight_scroll.setWidget(self.insight_panel)
        self.insight_scroll.setFixedWidth(320)
        self.insight_scroll.hide()
        self._drawer_open = False
        self.drawer_effect = QGraphicsOpacityEffect(self.insight_scroll)
        self.insight_scroll.setGraphicsEffect(self.drawer_effect)
        self.drawer_motion = QParallelAnimationGroup(self)
        self.drawer_slide = QPropertyAnimation(self.insight_scroll, b"pos", self)
        self.drawer_fade = QPropertyAnimation(self.drawer_effect, b"opacity", self)
        for animation in (self.drawer_slide, self.drawer_fade):
            animation.setDuration(280 if motion_enabled() else 0)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.drawer_motion.addAnimation(self.drawer_slide)
        self.drawer_motion.addAnimation(self.drawer_fade)
        self.drawer_motion.finished.connect(self.finish_insights)
        self.drawer_escape = QAction(self)
        self.drawer_escape.setShortcut("Escape")
        self.drawer_escape.setEnabled(False)
        self.drawer_escape.triggered.connect(lambda: self.drawer_button.setChecked(False))
        self.addAction(self.drawer_escape)
        outer.addLayout(body_row, 1)
        footer = QHBoxLayout()
        self.path_label = QLabel(str(Path(config.terminal.start_directory or Path.home())))
        self.path_label.setObjectName("path")
        self.path_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        footer.addWidget(self.path_label, 1)
        self.activity_label = QLabel("Ready")
        self.activity_label.setObjectName("muted")
        footer.addWidget(self.activity_label)
        keys = QLabel("Ctrl+C cancel   ·   Ctrl+Shift+V paste   ·   F11 full screen")
        keys.setStyleSheet("font-size:11px;color:#819783;margin-left:18px")
        footer.addWidget(keys)
        outer.addLayout(footer)
        self.setCentralWidget(container)
        self.activity_timer = QTimer(self)
        self.activity_timer.setInterval(250)
        self.activity_timer.timeout.connect(
            lambda: self.activity_label.setText(
                f"Interpretando · {time.monotonic() - self._processing_since:.1f} s"
            )
        )
        setting_action = QAction("Settings", self)
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
        # Qt requires objects to be registered before the JS client initializes.
        # The PTY reader starts only at Bridge.ready(), so early output stays
        # buffered until the single page load has attached its signal handlers.
        self.start_session()
        self.view.page().setWebChannel(self.channel)
        self.view.loadFinished.connect(self.loaded)
        self.view.setUrl(QUrl.fromLocalFile(str(asset_dir() / "web" / "index.html")))

    def loaded(self, ok: bool) -> None:
        if not ok:
            QMessageBox.critical(self, "Chameleon", "Could not load the local renderer.")
            return
        self.apply_settings()

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
            "#b5d89a"
            if status == "AI LOCAL"
            else "#e6c275"
            if processing
            else "#e87979"
            if status == "AI OFFLINE"
            else "#7d9287"
        )
        labels = {
            "AI LOCAL": "Local AI available",
            "PROCESSING": "Preparing your request",
            "AI OFFLINE": "Qwen offline · local rules ready",
            "AI CHECKING": "Checking Qwen",
            "AI DISABLED": "AI disabled · local rules ready",
            "AI ENABLED": "AI enabled",
            "SHELL EXITED": "Session ended",
        }
        labels.update(
            {
                "QWEN QUERYING": "Querying Qwen",
                "QWEN CHECKING FILE": "Checking real data",
                "QWEN RESPONDING": "Qwen is preparing a response",
            }
        )
        self.indicator.set_state(labels.get(status, status), color, processing)
        if processing:
            if not self.activity_timer.isActive():
                self._processing_since = time.monotonic()
            self.activity_timer.start()
        else:
            self.activity_timer.stop()
            self.activity_label.setText("Session ended" if status == "SHELL EXITED" else "Ready")

    def set_location(self, path: str) -> None:
        self.path_label.setToolTip(path)
        self.path_label.setText(
            self.path_label.fontMetrics().elidedText(
                path, Qt.TextElideMode.ElideMiddle, max(100, self.path_label.width())
            )
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "insight_scroll") and self._drawer_open:
            self.drawer_motion.stop()
            self.drawer_effect.setOpacity(1.0)
            QTimer.singleShot(0, self.position_insights)
        if hasattr(self, "path_label"):
            self.set_location(self.path_label.toolTip() or self.path_label.text())

    def change_route(self, index: int) -> None:
        self.config.ai.prefer_model = index == 1
        if self.session:
            self.session.config.ai.prefer_model = index == 1

    def position_insights(self) -> QPoint:
        body = self.centralWidget()
        if not body:
            return QPoint()
        top = self.workspace.mapTo(body, QPoint(0, 0)).y() + 8
        target = QPoint(body.width() - self.insight_scroll.width() - 30, top)
        self.insight_scroll.setFixedHeight(max(180, self.workspace.height() - 16))
        self.insight_scroll.move(target)
        return target

    def finish_insights(self) -> None:
        if not self._drawer_open:
            self.insight_scroll.hide()
            self.view.setFocus(Qt.FocusReason.OtherFocusReason)
            self.view.page().runJavaScript("if(window.focusTerminal)focusTerminal();")

    def toggle_insights(self, opened: bool) -> None:
        if not hasattr(self, "insight_scroll"):
            return
        self._drawer_open = opened
        self.drawer_button.setText("Close panel" if opened else "AI and permissions")
        self.drawer_escape.setEnabled(opened)
        self.drawer_motion.stop()
        was_visible = self.insight_scroll.isVisible()
        old_pos = self.insight_scroll.pos()
        old_opacity = self.drawer_effect.opacity()
        target = self.position_insights()
        self.insight_scroll.show()
        self.insight_scroll.raise_()
        self.drawer_slide.setStartValue(old_pos if was_visible else target + QPoint(22, 0))
        self.drawer_slide.setEndValue(target if opened else target + QPoint(22, 0))
        self.drawer_fade.setStartValue(old_opacity if was_visible else 0.0)
        self.drawer_fade.setEndValue(1.0 if opened else 0.0)
        self.drawer_motion.start()

    def change_model(self, tag: str) -> None:
        import threading

        if self.session and self.session.busy:
            self.session.cancel()
        self.config.ai.model = tag
        if self.session:
            self.session.config.ai.model = tag
            threading.Thread(target=self.session.check_ai, daemon=True).start()

    def change_access(self, index: int) -> None:
        if self.session and self.session.busy:
            self.session.cancel()
        self.config.safety.mode = self.access_picker.itemData(index)
        if self.session:
            self.session.config.safety = self.config.safety.model_copy(deep=True)
        self.access_picker.setToolTip(
            "No Chameleon blocks or confirmations · standard Windows user permissions."
            if self.config.safety.mode == "full"
            else "Profile for this window; save it in Settings to keep it."
        )

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
        dialog.setWindowTitle("Your terminal, in your words")
        dialog.resize(600, 440)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Start with a sentence.")
        title.setObjectName("heading")
        layout.addWidget(title)
        note = QLabel(
            "Type it directly in the terminal. Regular commands\nwork as usual; changes require confirmation."
        )
        note.setObjectName("muted")
        layout.addWidget(note)
        examples = QLabel(
            'chameleon ai create a file named notes.txt with content "Hello"\n\nchameleon ai create a folder named project\n\nchameleon ai go to Documents\n\nchameleon ai read notes.txt\n\nchameleon ai copy notes.txt to copy.txt\n\nchameleon ai find Python files larger than 1 MB'
        )
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
            self.on_failure(
                "Could not prepare the action. Run chameleon doctor and try again."
            )

    def _on_plan(self, plan: Plan, assessment: Assessment) -> None:
        if not self.session:
            return
        if self.session.cancel_requested.is_set():
            self.session.reset_prompt()
            return
        self.source_label.setText(plan.trace.label())
        self.answer_heading.setText(
            "Command"
            if self.config.ai.command_only
            else "Respuesta"
            if plan.intent == "explain"
            else "Proposed action"
        )
        self.answer_label.setText(plan.summary[:1200])
        if self.config.ai.command_only and plan.intent == "execute":
            from chameleon.platform.windows.shells import CmdAdapter, PowerShellAdapter

            adapter = (
                CmdAdapter(plan.policy_token)
                if plan.shell == "cmd"
                else PowerShellAdapter(plan.policy_token)
            )
            actual_command = "\n".join(adapter.render(a, self.session.cwd) for a in plan.actions)
            self.answer_label.setToolTip(actual_command)
            if plan.trace.source == "local" and any(
                a.kind in ("create", "copy", "move", "mkdir") for a in plan.actions
            ):
                self.answer_heading.setText("Local action")
                self.answer_label.setText(
                    "\n".join(
                        describe_action(a, self.session.cwd, plan.shell != "cmd")
                        for a in plan.actions
                    )[:800]
                )
            else:
                self.answer_label.setText(actual_command[:1600])
        if plan.intent == "explain":
            self.session.output.emit(
                "\r\nChameleon: " + plan.summary.replace("\n", "\r\n") + "\r\n"
            )
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
            commands = "\n\n".join(
                describe_action(a, self.session.cwd, plan.shell != "cmd") for a in plan.actions
            )
            confirmation = QMessageBox(self)
            confirmation.setWindowTitle("Chameleon needs confirmation")
            confirmation.setIcon(QMessageBox.Icon.Question)
            confirmation.setTextFormat(Qt.TextFormat.PlainText)
            confirmation.setText(
                "Review the changes before continuing.\n\n" + commands + "\n\n" + assessment.reason
            )
            confirmation.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            confirmation.setDefaultButton(QMessageBox.StandardButton.No)
            choice = confirmation.exec()
            if choice != QMessageBox.StandardButton.Yes:
                self.session.reset_prompt()
                return
        self.session.execute(plan, assessment)

    def on_failure(self, message: str) -> None:
        self.source_label.setText("Request incomplete · no new action was executed.")
        self.answer_heading.setText("Needs attention")
        self.answer_label.setText(message)
        if self.session:
            self.session.output.emit("\r\nChameleon: " + message.replace("\n", "\r\n") + "\r\n")
            self.session.reset_prompt()

    def settings(self) -> None:
        from chameleon.setup.settings import SettingsDialog

        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            if self.session and self.session.busy:
                self.session.cancel()
            self.config = dialog.config
            if self.session:
                self.session.update_config(self.config)
            self.route.setCurrentIndex(1 if self.config.ai.prefer_model else 0)
            if self.model_picker.findText(self.config.ai.model) < 0:
                self.model_picker.addItem(self.config.ai.model)
            self.model_picker.setCurrentText(self.config.ai.model)
            self.access_picker.setCurrentIndex(self.access_picker.findData(self.config.safety.mode))
            self.apply_settings()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.session:
            self.session.close()
        event.accept()
