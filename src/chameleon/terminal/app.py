import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from chameleon.core.config import asset_dir, data_dir, load_config
from chameleon.core.privacy import configure_logging

STYLE = """QWidget{background:#080d0b;color:#d8ecdf;font-family:Segoe UI;font-size:13px} QToolBar{border-bottom:1px solid #244b36;padding:8px} QPushButton,QToolButton{background:#133522;border:1px solid #286544;padding:8px 16px;border-radius:4px} QPushButton:hover,QToolButton:hover{background:#205035} QLineEdit,QSpinBox,QComboBox,QTextEdit{background:#101d16;border:1px solid #286544;padding:5px} QTabWidget::pane{border:1px solid #244b36} QTabBar::tab{padding:9px;background:#133522} QTabBar::tab:selected{color:#51fa8b} QCheckBox{padding:4px} """


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication(argv or sys.argv)
    app.setApplicationName("Chameleon AI")
    app.setOrganizationName("Chameleon AI")
    app.setWindowIcon(QIcon(str(asset_dir() / "icons" / "chameleon.ico")))
    app.setStyleSheet(STYLE)
    return app


def main(argv: list[str] | None = None) -> int:
    app = create_application(argv)
    config, warning = load_config()
    configure_logging(data_dir())
    if warning:
        QMessageBox.warning(None, "Chameleon", warning)
    from chameleon.terminal.window import TerminalWindow

    window = TerminalWindow(config)
    window.show()
    args = argv or sys.argv[1:]
    if "--smoke" in args:
        from pathlib import Path

        from chameleon.terminal.smoke import attach_smoke

        attach_smoke(app, window, Path(args[args.index("--smoke") + 1]))
    return app.exec()
