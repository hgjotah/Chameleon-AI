import logging

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication

from chameleon.terminal.session import TerminalSession


class Bridge(QObject):
    output = Signal(str)
    status = Signal(str)
    initialized = Signal()

    def __init__(self, session: TerminalSession) -> None:
        super().__init__()
        self.session = session
        session.output.connect(self.output)
        session.status.connect(self.status)

    @Slot(str)
    def input(self, data: str) -> None:
        try:
            self.session.data(data)
        except Exception as exc:
            logging.getLogger("chameleon").warning("Shell input failed: %s", type(exc).__name__)
            self.session.closed = True
            self.session.exited.emit()

    @Slot()
    def ready(self) -> None:
        self.session.start()
        self.initialized.emit()

    @Slot(str)
    def copyClipboard(self, text: str) -> None:
        QApplication.clipboard().setText(text)

    @Slot(result=str)
    def pasteClipboard(self) -> str:
        return QApplication.clipboard().text()

    @Slot(str)
    def openLink(self, uri: str) -> None:
        url = QUrl(uri)
        if url.scheme() in ("http", "https"):
            QDesktopServices.openUrl(url)

    @Slot(str)
    def submit(self, line: str) -> None:
        self.session.submit(line)

    @Slot(str, str, result=bool)
    def prompt(self, token: str, cwd: str) -> bool:
        return self.session.prompt(token, cwd)

    @Slot(int, int)
    def resize(self, rows: int, cols: int) -> None:
        if self.session.closed:
            return
        try:
            self.session.backend.resize(rows, cols)
        except Exception as exc:
            logging.getLogger("chameleon").warning("Shell resize failed: %s", type(exc).__name__)
            self.session.closed = True
            self.session.exited.emit()

    @Slot()
    def ctrlBreak(self) -> None:
        self.session.backend.interrupt(True)
