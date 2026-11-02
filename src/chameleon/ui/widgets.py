import math

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QWidget

from chameleon.core.config import asset_dir
from chameleon.ui.controls import MotionButton as MotionButton
from chameleon.ui.motion import motion_enabled


class BrandMark(QWidget):
    def __init__(self, parent: QWidget | None = None, size: int = 52) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.logo = QPixmap(str(asset_dir() / "icons/chameleon.png"))
        self.setAccessibleName("Camaleón Chameleon")

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawPixmap(self.rect(), self.logo)
        p.end()


class StatusPill(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Comprobando IA", parent)
        self.color = "#91a58d"
        self._full_text = "Comprobando IA"
        self.phase = 0.0
        self.setContentsMargins(23, 5, 12, 5)
        self.setFixedHeight(30)
        self.setMaximumWidth(230)
        self.timer = QTimer(self)
        self.timer.setInterval(45)
        self.timer.timeout.connect(self.pulse)
        self.set_state("Comprobando IA", "#91a58d")

    def set_state(self, text: str, color: str, active: bool = False) -> None:
        self._full_text = text
        self.setToolTip(text)
        self.color = color
        self.setStyleSheet(
            f"background:rgba(24,39,28,130);color:{color};border:1px solid rgba(164,190,148,36);border-radius:15px;font-size:11px;"
        )
        self.timer.start() if active and motion_enabled() else self.timer.stop()
        self._elide()
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(min(230, self.fontMetrics().horizontalAdvance(self._full_text) + 38), 30)

    def minimumSizeHint(self) -> QSize:
        return QSize(95, 30)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._elide()

    def _elide(self) -> None:
        self.setText(self.fontMetrics().elidedText(self._full_text, Qt.TextElideMode.ElideRight, max(35, self.width() - 35)))

    def pulse(self) -> None:
        self.phase += 0.16
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self.color)
        color.setAlphaF(0.6 + 0.4 * math.sin(self.phase) ** 2 if self.timer.isActive() else 1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(QRectF(10, self.height() / 2 - 3, 6, 6))
        p.end()
