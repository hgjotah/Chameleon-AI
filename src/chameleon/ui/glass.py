"""Native PySide6 layout adapter for the MIT PyGlass renderer (see provenance)."""

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPaintEvent,
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
            image.fill(QColor("#0a1021"))
            painter = QPainter(image)
            for x, y, r, color in (
                (0.05, 0.12, 0.75, "#17495c"),
                (0.92, 0.0, 0.65, "#493b72"),
                (0.72, 1.1, 0.7, "#133f45"),
            ):
                glow = QRadialGradient(
                    self.width() * x, self.height() * y, max(self.width(), self.height()) * r
                )
                glow.setColorAt(0, QColor(color))
                glow.setColorAt(1, QColor(10, 16, 33, 0))
                painter.fillRect(self.rect(), glow)
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
        self._pending = QTimer(self)
        self._pending.setSingleShot(True)
        self._pending.setInterval(130)
        self._pending.timeout.connect(self.refresh_glass)
        self._style = GlassStyle(
            shadow_layers=0,
            tint_top=24,
            tint_bottom=10,
            rim_top=105,
            rim_bottom=65,
            rim_mid=22,
            sheen_alpha=12,
            rim_width=1.0,
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._pending.start()

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
            GlassMaterial(thickness=0.24, frost=0.18, pad=32, bevel=24, strength=14, chroma=0.025),
            width,
            height,
            20 * scale,
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
            20,
            self._glass,
            style=self._style,
        )


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
