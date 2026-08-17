import logging

from PySide6.QtCore import QObject, Signal

from sniplens.capture import BackendUnavailable, Success


class LinuxRegionCapture(QObject):
    """Routes region capture to the backend matching the active session:
    the XDG Screenshot portal on Wayland, native capture with an own region
    selection overlay on X11."""

    completed = Signal(object)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._backend = None
        self._from_app_trigger = False

    def stop(self):
        if self._backend is not None:
            self._backend.stop()

    def request_region(self, from_app_trigger=True):
        if self._backend is not None:
            logging.info("[Snip] A capture is already in progress, ignoring the request.")
            return
        platform = self._app.platformName()
        if platform == "wayland":
            from sniplens.capture.portal import PortalRegionCapture

            self._backend = PortalRegionCapture(self)
        elif platform == "xcb":
            from sniplens.capture.x11_capture import X11RegionCapture

            self._backend = X11RegionCapture(self)
        else:
            logging.error("[Snip] Unsupported window system %r for region capture.", platform)
            self.completed.emit(BackendUnavailable(f"unsupported window system: {platform}"))
            return
        self._from_app_trigger = from_app_trigger
        self._backend.completed.connect(self._on_backend_completed)
        self._backend.request_region()

    def _on_backend_completed(self, outcome):
        if isinstance(outcome, Success):
            outcome.from_app_trigger = self._from_app_trigger
        self._backend.deleteLater()
        self._backend = None
        self.completed.emit(outcome)
