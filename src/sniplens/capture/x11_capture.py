import logging

from PySide6.QtCore import QObject, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from sniplens.capture import Cancelled, Success

MIN_SELECTION = 3


def virtual_desktop_canvas():
    """Grabs every screen into one image covering the union of all monitor
    geometries, scaled to the primary screen's device pixel ratio."""
    screens = QGuiApplication.screens()
    union = screens[0].geometry()
    for screen in screens[1:]:
        union = union.united(screen.geometry())
    dpr = QGuiApplication.primaryScreen().devicePixelRatio()
    canvas = QImage(
        round(union.width() * dpr), round(union.height() * dpr), QImage.Format.Format_ARGB32
    )
    painter = QPainter(canvas)
    for screen in screens:
        grab = screen.grabWindow(0).toImage()
        logical = QRectF(screen.geometry().translated(-union.topLeft()))
        target = QRectF(
            logical.x() * dpr, logical.y() * dpr, logical.width() * dpr, logical.height() * dpr
        )
        painter.drawImage(target, grab)
    painter.end()
    return canvas, union, dpr


class SelectionOverlay(QWidget):
    """Full-desktop dimmed overlay the user drags a rectangle on."""

    accepted = Signal(QRect)
    cancelled = Signal()

    def __init__(self, canvas, union, dpr):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.X11BypassWindowManagerHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._canvas = canvas
        self._dpr = dpr
        self._origin = None
        self._current = None
        self.setWindowTitle("Snipping Lens")
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(union)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._current = QRect(self._origin, self._origin)
            self.update()

    def mouseMoveEvent(self, event):
        if self._origin is not None:
            self._current = QRect(self._origin, event.position().toPoint()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self._origin is None:
            return
        rect = QRect(self._origin, event.position().toPoint()).normalized()
        self._origin = None
        if rect.width() < MIN_SELECTION or rect.height() < MIN_SELECTION:
            self.cancelled.emit()
        else:
            self.accepted.emit(rect)
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(QRectF(0, 0, self.width(), self.height()), self._canvas)
        painter.fillRect(QRect(0, 0, self.width(), self.height()), QColor(0, 0, 0, 128))
        if self._current is not None and self._current.width() > 0:
            source = QRectF(
                self._current.x() * self._dpr,
                self._current.y() * self._dpr,
                self._current.width() * self._dpr,
                self._current.height() * self._dpr,
            )
            painter.drawImage(QRectF(self._current), self._canvas, source)
            painter.setPen(QPen(QColor(255, 255, 255, 220), 1))
            painter.drawRect(QRectF(self._current))


class X11RegionCapture(QObject):
    """Captures the root desktop and lets the user pick the region with the
    selection overlay, without relying on any installed screenshot tool."""

    completed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._overlay = None
        self._canvas = None
        self._dpr = 1.0

    def stop(self):
        if self._overlay is not None:
            self._overlay.close()

    def request_region(self):
        if self._overlay is not None:
            logging.info("[Snip] A selection is already in progress, ignoring the request.")
            return
        self._canvas, union, self._dpr = virtual_desktop_canvas()
        self._overlay = SelectionOverlay(self._canvas, union, self._dpr)
        self._overlay.accepted.connect(self._on_accepted)
        self._overlay.cancelled.connect(self._on_cancelled)
        self._overlay.show()
        self._overlay.raise_()
        self._overlay.activateWindow()

    def _on_accepted(self, rect):
        physical = QRect(
            round(rect.x() * self._dpr),
            round(rect.y() * self._dpr),
            round(rect.width() * self._dpr),
            round(rect.height() * self._dpr),
        )
        self._overlay = None
        self.completed.emit(Success(self._canvas.copy(physical)))

    def _on_cancelled(self):
        self._overlay = None
        self.completed.emit(Cancelled("selection dismissed"))
