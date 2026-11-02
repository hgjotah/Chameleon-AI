"""Native PySide6 layout adapter for the MIT PyGlass renderer (see provenance)."""

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QRadialGradient,
    QResizeEvent,
)
from PySide6.QtWidgets import QFrame, QWidget

from chameleon.ui.vendor.pyglass.effect import GlassRenderer, GlassStyle, paint_glass
from chameleon.ui.vendor.pyglass.refract import GlassMaterial, qimage_to_array


class GlassCanvas(QWidget):
    """An in-app backdrop; never captures desktop pixels or other applications."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("glassCanvas")
        self._scene = QPixmap()

    def scene_pixmap(self) -> QPixmap:
        if self._scene.size() != self.size():
            image = QImage(self.size(), QImage.Format.Format_RGBA8888)
            image.fill(QColor("#0b110d"))
            painter = QPainter(image)
            for x, y, r, color in (
                (0.16, -0.15, 0.8, "#28432c"),
                (1.1, 0.8, 0.7, "#1d3324"),
            ):
                glow = QRadialGradient(
                    self.width() * x, self.height() * y, max(self.width(), self.height()) * r
                )
                glow.setColorAt(0, QColor(color))
                glow.setColorAt(1, QColor(11, 17, 13, 0))
                painter.fillRect(self.rect(), glow)
            # Quiet contours give the lens actual detail to bend. Unlike desktop
            # capture, all pixels belong to this application.
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            for index in range(5):
                path = QPainterPath(QPointF(-120, 25 + index * 19))
                path.cubicTo(
                    self.width() * 0.25,
                    240 + index * 18,
                    self.width() * 0.62,
                    -155 + index * 23,
                    self.width() + 100,
                    110 + index * 24,
                )
                painter.setPen(QPen(QColor(151, 185, 135, 8 if index != 2 else 19), 1.1))
                painter.drawPath(path)
            painter.end()
            self._scene = QPixmap.fromImage(image)
        return self._scene

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.scene_pixmap())


class GlassFrame(QFrame):
    """Cached refractive slab, driven by upstream optics and compositing."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._glass: QPixmap | None = None
        self._light = QPointF(80, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._pending = QTimer(self)
        self._pending.setSingleShot(True)
        self._pending.setInterval(130)
        self._pending.timeout.connect(self.refresh_glass)
        self._style = GlassStyle(
            shadow_layers=0,
            tint_top=12,
            tint_bottom=4,
            rim_top=100,
            rim_bottom=30,
            rim_mid=18,
            sheen_alpha=8,
            rim_width=1.0,
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._pending.start()

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.HoverMove:
            self._light = event.position()  # type: ignore[attr-defined]
            self.update()
        elif event.type() == QEvent.Type.Move and hasattr(self, "_pending"):
            self._pending.start()
        return super().event(event)

    def showEvent(self, event: object) -> None:
        super().showEvent(event)  # type: ignore[arg-type]
        self._pending.start()

    def refresh_glass(self) -> None:
        if self.width() < 4 or self.height() < 4:
            return
        backdrop = self.parentWidget()
        while backdrop and not isinstance(backdrop, GlassCanvas):
            backdrop = backdrop.parentWidget()
        if not isinstance(backdrop, GlassCanvas):
            return
        # Bound array/kernel allocation. The lens is a decoration, not a reason
        # to compete with the local model for CPU/RAM during typing/generation.
        scale = min(1.0, 420 / max(self.width(), self.height()))
        scene = backdrop.scene_pixmap().toImage()
        scene = scene.scaled(
            max(1, int(scene.width() * scale)),
            max(1, int(scene.height() * scale)),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        origin = self.mapTo(backdrop, QPoint(0, 0))
        width = max(2, int(self.width() * scale))
        height = max(2, int(self.height() * scale))
        renderer = GlassRenderer(
            GlassMaterial(
                thickness=0.44,
                frost=0.07,
                pad=max(12, 34 * scale),
                bevel=20 * scale,
                strength=12 * scale,
                chroma=0.002,
                disp_glow=0,
                reflect=0.55,
                ior_edge=2.6,
            ),
            width,
            height,
            18 * scale,
        )
        refracted = renderer.refract(
            qimage_to_array(scene), QPoint(int(origin.x() * scale), int(origin.y() * scale)), 1.0
        )
        if refracted:
            self._glass = refracted.scaled(
                self.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        paint_glass(
            painter,
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            18,
            self._glass,
            style=self._style,
        )
        # Cursor-lit rim, adapted from Motion Primitives' Spotlight coordinates.
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 18, 18)
        light = QRadialGradient(self._light, 210)
        light.setColorAt(0, QColor(226, 248, 214, 105))
        light.setColorAt(1, QColor(226, 248, 214, 0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(light, 1.1))
        painter.drawPath(path)


def install_glass(dialog: QWidget) -> None:
    """Paint an app-owned glass backdrop behind native dialog controls."""
    canvas = GlassCanvas(dialog)
    canvas.lower()
    canvas.setGeometry(dialog.rect())
    from PySide6.QtCore import QEvent, QObject

    class Follower(QObject):
        def eventFilter(self, watched: object, event: QEvent) -> bool:
            if event.type() == QEvent.Type.Resize:
                canvas.setGeometry(dialog.rect())
            return False

    follower = Follower(dialog)
    dialog.installEventFilter(follower)
    dialog._glass_background = (canvas, follower)  # type: ignore[attr-defined]
