import ctypes
import logging
import subprocess

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QImage

from sniplens.capture import Cancelled, CaptureFailed, Success

SNIP_TIMEOUT_MS = 120000


def clipboard_sequence_number():
    return ctypes.windll.user32.GetClipboardSequenceNumber()


class WindowsSnipCapture(QObject):
    """Region capture through the Windows Snipping Tool. One armed transaction
    at a time: record the clipboard sequence, invoke ms-screenclip:, then only
    a later clipboard update carrying an image completes the transaction.
    Passive clipboard images (e.g. a plain Win+Shift+S) surface separately."""

    completed = Signal(object)
    image_copied = Signal(QImage)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clipboard = QGuiApplication.clipboard()
        self._clipboard.dataChanged.connect(self._on_clipboard_changed)
        self._timeout = QTimer(self, singleShot=True, interval=SNIP_TIMEOUT_MS)
        self._timeout.timeout.connect(self._on_timeout)
        self._armed_sequence = None
        self._from_app_trigger = False

    def request_region(self, from_app_trigger=True):
        if self._armed_sequence is not None:
            self._timeout.stop()
        self._armed_sequence = clipboard_sequence_number()
        self._from_app_trigger = from_app_trigger
        try:
            subprocess.Popen(["explorer.exe", "ms-screenclip:"])
        except OSError as e:
            self._armed_sequence = None
            logging.error("[Snip] Failed to launch the Snipping Tool: %s", e)
            self.completed.emit(CaptureFailed(f"failed to launch the Snipping Tool: {e}"))
            return
        self._timeout.start()
        logging.info("[Snip] Snipping Tool launched, waiting for the clipboard image.")

    def stop(self):
        self._timeout.stop()
        self._armed_sequence = None

    def _on_clipboard_changed(self):
        mime = self._clipboard.mimeData()
        if self._armed_sequence is not None:
            if clipboard_sequence_number() > self._armed_sequence and mime.hasImage():
                self._timeout.stop()
                self._armed_sequence = None
                logging.info("[Snip] Clipboard image received, transaction completed.")
                self.completed.emit(Success(self._clipboard.image(), self._from_app_trigger))
            return
        if mime.hasImage():
            self.image_copied.emit(self._clipboard.image())

    def _on_timeout(self):
        self._armed_sequence = None
        logging.info("[Snip] Snipping Tool transaction timed out.")
        self.completed.emit(Cancelled("timed out"))
