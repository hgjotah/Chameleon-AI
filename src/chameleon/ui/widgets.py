import math

from PySide6.QtCore import Property, QEasingCurve, QEvent, QPropertyAnimation, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from chameleon.core.config import asset_dir


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


class MotionButton(QPushButton):
    """Native accessible button with a short, reversible hover transition."""
    def __init__(self, text: str, parent: QWidget | None = None, primary: bool = False) -> None:
        super().__init__(text, parent)
        self.primary = primary
        self._hover = 0.0
        self.animation = QPropertyAnimation(self, b"hoverAmount", self)
        self.animation.setDuration(160)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMinimumHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def get_hover(self) -> float:
        return self._hover

    def set_hover(self, value: float) -> None:
        self._hover = value
        self.update()

    hoverAmount = Property(float, get_hover, set_hover)

    def event(self, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.Enter, QEvent.Type.Leave):
            self.animation.stop()
            self.animation.setStartValue(self._hover)
            self.animation.setEndValue(1.0 if event.type() == QEvent.Type.Enter else 0.0)
            self.animation.start()
        return super().event(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        a = QColor("#71ddb3" if self.primary else "#172d34")
        b = QColor("#a0f0d2" if self.primary else "#2a4d52")
        value = self._hover if self.isEnabled() else 0
        color = QColor.fromRgbF(a.redF() * (1 - value) + b.redF() * value, a.greenF() * (1 - value) + b.greenF() * value, a.blueF() * (1 - value) + b.blueF() * value)
        if self.isDown():
            color = color.darker(115)
        if not self.isEnabled():
            color = QColor("#192330")
        p.setBrush(color)
        p.setPen(QPen(QColor("#93e9c9" if self.primary and self.isEnabled() else "#3a5b60"), 1))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 9, 9)
        p.setPen(QColor("#0a2b23" if self.primary and self.isEnabled() else "#e0ebf5" if self.isEnabled() else "#76869a"))
        font = self.font()
        font.setWeight(QFont.Weight.DemiBold)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#e4fff4"), 1, Qt.PenStyle.DotLine))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(4, 4, -4, -4), 7, 7)
        p.end()


class StatusPill(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Comprobando IA", parent)
        self.color = "#94a7bf"
        self.phase = 0.0
        self.setContentsMargins(23, 5, 12, 5)
        self.setFixedHeight(30)
        self.timer = QTimer(self)
        self.timer.setInterval(45)
        self.timer.timeout.connect(self.pulse)
        self.set_state("Comprobando IA", "#94a7bf")

    def set_state(self, text: str, color: str, active: bool = False) -> None:
        self.setText(text)
        self.color = color
        self.setStyleSheet(f"background:#15202e;color:{color};border:1px solid #304052;border-radius:15px;font-size:11px;")
        self.timer.start() if active else self.timer.stop()
        self.update()

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
