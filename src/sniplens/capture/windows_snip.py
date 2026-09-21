import ctypes
import logging
import subprocess

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QGuiApplication

from sniplens.capture import Cancelled, CaptureFailed, Success

SNIP_TIMEOUT_MS = 120000

# the sequence number is a DWORD; the default ctypes restype would wrap it into
# a signed int and make the comparison against an armed value go backwards
clipboard_sequence_number = ctypes.windll.user32.GetClipboardSequenceNumber
clipboard_sequence_number.restype = ctypes.c_uint
clipboard_sequence_number.argtypes = ()


class WindowsSnipCapture(QObject):
    """Region capture through the Windows Snipping Tool. Every route into the
    Snipping Tool arms one transaction - the app launching ms-screenclip:, or
    the user pressing the system snip keys - and only a later clipboard update
    carrying an image completes it. A clipboard image that no snip gesture
    armed is not a capture and is ignored."""

    completed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clipboard = QGuiApplication.clipboard()
        self._clipboard.dataChanged.connect(self._on_clipboard_changed)
        self._timeout = QTimer(self, singleShot=True, interval=SNIP_TIMEOUT_MS)
        self._timeout.timeout.connect(self._on_timeout)
        self._armed_sequence = None

    def request_region(self):
        self._arm()
        try:
            subprocess.Popen(["explorer.exe", "ms-screenclip:"])
        except OSError as e:
            self._timeout.stop()
            self._armed_sequence = None
            logging.error("[Snip] Failed to launch the Snipping Tool: %s", e)
            self.completed.emit(CaptureFailed(f"failed to launch the Snipping Tool: {e}"))
            return
        logging.info("[Snip] Snipping Tool launched, waiting for the clipboard image.")

    def arm_for_system_snip(self):
        """The user reached the Snipping Tool without us - Win+Shift+S or Print
        Screen. Windows opens it, so this only arms the transaction."""
        self._arm()
        logging.info("[Snip] System snip key pressed, waiting for the clipboard image.")

    def stop(self):
        self._clipboard.dataChanged.disconnect(self._on_clipboard_changed)
        self._timeout.stop()
        self._armed_sequence = None

    def _arm(self):
        self._armed_sequence = clipboard_sequence_number()
        self._timeout.start()

    def _on_clipboard_changed(self):
        if self._armed_sequence is None:
            return
        if clipboard_sequence_number() <= self._armed_sequence:
            return
        if not self._clipboard.mimeData().hasImage():
            return
        self._timeout.stop()
        self._armed_sequence = None
        logging.info("[Snip] Clipboard image received, transaction completed.")
        self.completed.emit(Success(self._clipboard.image()))

    def _on_timeout(self):
        self._armed_sequence = None
        logging.info("[Snip] Snipping Tool transaction timed out.")
        self.completed.emit(Cancelled("timed out"))
