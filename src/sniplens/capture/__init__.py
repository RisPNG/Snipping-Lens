from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from sniplens import paths


@dataclass
class Success:
    image: QImage
    from_app_trigger: bool = False


@dataclass
class Cancelled:
    reason: str = ""


@dataclass
class PermissionDenied:
    message: str


@dataclass
class BackendUnavailable:
    message: str


@dataclass
class CaptureFailed:
    message: str


def create_capture_service(app):
    """The single region-capture entry point; everything above this layer is
    unaware of Windows, Wayland, X11 or portals."""
    if paths.IS_WINDOWS:
        from sniplens.capture.windows_snip import WindowsSnipCapture

        return WindowsSnipCapture()
    from sniplens.capture.linux_capture import LinuxRegionCapture

    return LinuxRegionCapture(app)
