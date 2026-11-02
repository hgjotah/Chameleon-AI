"""Native adaptation of Codrops MagneticButtons + Motion Primitives Spotlight.

See assets/licenses/ui-motion for the original sources, pinned revisions and MIT
notices. Only the painted content moves; keyboard semantics and hit areas stay put.
"""

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QFocusEvent,
    QFont,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QPushButton, QWidget

from chameleon.ui.motion import motion_enabled


class MotionButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None, primary: bool = False) -> None:
        super().__init__(text, parent)
        self.primary = primary
        self._motion = motion_enabled()
        self._hover = 0.0
        self._press = 0.0
        self._keyboard_focus = False
        self._tx = self._ty = self._target_x = self._target_y = 0.0
        self._mouse = QPointF(30, 10)
        self.setMinimumHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.animation = QPropertyAnimation(self, b"hoverAmount", self)
        self.animation.setDuration(340 if self._motion else 0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.press_animation = QPropertyAnimation(self, b"pressAmount", self)
        self.press_animation.setDuration(170 if self._motion else 0)
        self.press_animation.setEasingCurve(QEasingCurve.Type.OutBack)
        self.magnetic_timer = QTimer(self)
        self.magnetic_timer.setInterval(16)
        self.magnetic_timer.timeout.connect(self._step)
        self.pressed.connect(lambda: self._animate_press(1.0))
        self.released.connect(lambda: self._animate_press(0.0))

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(hint.width() + (32 if self.primary else 8), max(42, hint.height()))

    def get_hover(self) -> float:
        return self._hover

    def set_hover(self, value: float) -> None:
        self._hover = value
        self.update()

    hoverAmount = Property(float, get_hover, set_hover)

    def get_press(self) -> float:
        return self._press

    def set_press(self, value: float) -> None:
        self._press = value
        self.update()

    pressAmount = Property(float, get_press, set_press)

    def _animate_press(self, target: float) -> None:
        self.press_animation.stop()
        self.press_animation.setStartValue(self._press)
        self.press_animation.setEndValue(target)
        self.press_animation.start()

    def _step(self) -> None:
        # Codrops demo1: pointer-relative translation + lerp(..., amt=.1), with
        # counter-translation of text by .6. Native controls use smaller bounds.
        self._tx = 0.9 * self._tx + 0.1 * self._target_x
        self._ty = 0.9 * self._ty + 0.1 * self._target_y
        if abs(self._tx - self._target_x) + abs(self._ty - self._target_y) < 0.025:
            self._tx, self._ty = self._target_x, self._target_y
            self.magnetic_timer.stop()
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._mouse = event.position()
        if self._motion and self.isEnabled():
            self._target_x = max(-2.6, min(2.6, (self._mouse.x() - self.width() / 2) * 0.3))
            self._target_y = max(-1.8, min(1.8, (self._mouse.y() - self.height() / 2) * 0.3))
            self.magnetic_timer.start()
        self.update()
        super().mouseMoveEvent(event)

    def event(self, event: QEvent) -> bool:
        kind = event.type()
        if hasattr(self, "animation"):
            if kind == QEvent.Type.FocusIn and isinstance(event, QFocusEvent):
                self._keyboard_focus = event.reason() in (
                    Qt.FocusReason.TabFocusReason,
                    Qt.FocusReason.BacktabFocusReason,
                    Qt.FocusReason.ShortcutFocusReason,
                )
            elif kind == QEvent.Type.FocusOut:
                self._keyboard_focus = False
            if kind in (
                QEvent.Type.Enter,
                QEvent.Type.Leave,
                QEvent.Type.FocusIn,
                QEvent.Type.FocusOut,
            ):
                target = (
                    1.0
                    if (
                        kind in (QEvent.Type.Enter, QEvent.Type.FocusIn)
                        or (kind == QEvent.Type.Leave and self._keyboard_focus)
                    )
                    else 0.0
                )
                self.animation.stop()
                self.animation.setStartValue(self._hover)
                self.animation.setEndValue(target)
                self.animation.start()
                if kind == QEvent.Type.Leave:
                    self._target_x = self._target_y = 0.0
                    if self._motion:
                        self.magnetic_timer.start()
            elif kind in (QEvent.Type.Hide, QEvent.Type.EnabledChange) and (
                not self.isVisible() or not self.isEnabled()
            ):
                self.magnetic_timer.stop()
                self.animation.stop()
                self.press_animation.stop()
                self._tx = self._ty = self._hover = self._press = 0.0
        return super().event(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(self.width() / 2 + self._tx, self.height() / 2 + self._ty)
        scale = 1 - 0.026 * self._press
        p.scale(scale, scale)
        p.translate(-self.width() / 2, -self.height() / 2)
        rect = QRectF(self.rect()).adjusted(3.5, 3.5, -3.5, -3.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        value = max(self._hover, 0.4 if self.isChecked() else 0) if self.isEnabled() else 0
        p.save()
        p.setClipPath(path)
        fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
        if self.primary and self.isEnabled():
            fill.setColorAt(0, QColor("#c3dca6"))
            fill.setColorAt(1, QColor("#9dbc83"))
        else:
            fill.setColorAt(
                0,
                QColor(
                    44, 65, 48, int(105 + value * 60) if not self.isFlat() else int(value * 110)
                ),
            )
            fill.setColorAt(
                1,
                QColor(
                    26, 43, 31, int(160 + value * 50) if not self.isFlat() else int(value * 120)
                ),
            )
        p.fillPath(path, fill)
        # Spotlight uses the cursor in local coordinates, clipped to the surface.
        glow = QRadialGradient(self._mouse, max(75, self.width() * 0.8))
        glow.setColorAt(0, QColor(235, 255, 214, int(value * (65 if self.primary else 23))))
        glow.setColorAt(1, QColor(235, 255, 214, 0))
        p.fillRect(rect, glow)
        if self._motion and 0 < value < 1:
            sweep = QLinearGradient(
                self.width() * (value * 1.8 - 0.6),
                0,
                self.width() * (value * 1.8 - 0.1),
                self.height(),
            )
            sweep.setColorAt(0, QColor(244, 255, 223, 0))
            sweep.setColorAt(0.5, QColor(244, 255, 223, int(25 * value)))
            sweep.setColorAt(1, QColor(244, 255, 223, 0))
            p.fillRect(rect, sweep)
        p.restore()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(
            QPen(
                QColor(211, 236, 182, int(110 + 55 * value))
                if self.primary
                else QColor(
                    146, 180, 139, int(35 + 60 * value) if not self.isFlat() else int(70 * value)
                ),
                1,
            )
        )
        p.drawPath(path)
        p.setPen(
            QColor(
                "#132216"
                if self.primary and self.isEnabled()
                else "#e1ecdd"
                if self.isEnabled()
                else "#637a68"
            )
        )
        font = self.font()
        font.setWeight(QFont.Weight.DemiBold)
        p.setFont(font)
        text_rect = rect.translated(-self._tx * 0.6, -self._ty * 0.6)
        if self.primary:
            text_rect.adjust(7, 0, -21, 0)
        label = self.fontMetrics().elidedText(
            self.text(), Qt.TextElideMode.ElideRight, int(text_rect.width() - 10)
        )
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)
        if self.primary:
            x = rect.right() - 19 + 3 * value
            y = rect.center().y()
            p.setPen(QPen(QColor("#1d3520"), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(x - 4, y), QPointF(x + 4, y))
            p.drawLine(QPointF(x + 1, y - 3), QPointF(x + 4, y))
            p.drawLine(QPointF(x + 1, y + 3), QPointF(x + 4, y))
        if self.hasFocus() and self._keyboard_focus:
            p.setPen(QPen(QColor("#c9e9b2"), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 14, 14)
        p.end()
