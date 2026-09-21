import asyncio
import contextlib
import itertools
import logging
import os
import threading

from dbus_fast import BusType, Message, MessageType, Variant
from dbus_fast.aio import MessageBus
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QImage

from sniplens.capture import BackendUnavailable, Cancelled, CaptureFailed, PermissionDenied, Success

PORTAL_SERVICE = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SCREENSHOT_INTERFACE = "org.freedesktop.portal.Screenshot"
REQUEST_INTERFACE = "org.freedesktop.portal.Request"
REQUEST_TIMEOUT = 120
AREA_TARGET = 4

# the portal is not running, or its backend serves no Screenshot interface
UNAVAILABLE_ERRORS = (
    "org.freedesktop.DBus.Error.ServiceUnknown",
    "org.freedesktop.DBus.Error.UnknownInterface",
    "org.freedesktop.DBus.Error.UnknownObject",
)

PORTAL_BACKEND_PACKAGES = {
    "gnome": "xdg-desktop-portal-gnome",
    "kde": "xdg-desktop-portal-kde",
    "cosmic": "xdg-desktop-portal-cosmic",
    "deepin": "xdg-desktop-portal-deepin",
    "x-cinnamon": "xdg-desktop-portal-gtk",
    "xfce": "xdg-desktop-portal-gtk",
    "mate": "xdg-desktop-portal-gtk",
    "budgie": "xdg-desktop-portal-gtk",
    "lxqt": "xdg-desktop-portal-gtk",
    "sway": "xdg-desktop-portal-wlr",
    "hyprland": "xdg-desktop-portal-hyprland",
    "river": "xdg-desktop-portal-wlr",
    "labwc": "xdg-desktop-portal-wlr",
    "wlroots": "xdg-desktop-portal-wlr",
}


def portal_unavailable_message():
    """Names the backend package matching the running desktop so the user
    knows exactly what to install."""
    desktops = [
        part.strip().lower()
        for part in os.environ.get("XDG_CURRENT_DESKTOP", "").replace(";", ":").split(":")
        if part.strip()
    ]
    for desktop in desktops:
        package = PORTAL_BACKEND_PACKAGES.get(desktop)
        if package is not None:
            return (
                "the XDG Desktop Portal does not provide a Screenshot interface; "
                f"for {desktop} install {package}"
            )
    return (
        "the XDG Desktop Portal does not provide a Screenshot interface; "
        "install the portal backend for your desktop "
        "(e.g. xdg-desktop-portal-gnome, -kde, -gtk or -wlr)"
    )


class PortalRegionCapture(QObject):
    """Region capture through the XDG Desktop Portal Screenshot interface,
    which hands compositor permissions and the selection UI to the desktop."""

    completed = Signal(object)

    _tokens = itertools.count(1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._busy = False
        self._loop = None
        self._bus = None
        self._request_path = None

    def request_region(self):
        if self._busy:
            return
        self._busy = True
        threading.Thread(target=self._run, name="portal-capture", daemon=True).start()

    def stop(self):
        """Closing the request makes the desktop dismiss its own selection UI
        and answer with a Response, so the capture ends the ordinary way
        instead of being abandoned with the overlay still on screen."""
        if self._loop is not None and self._request_path is not None:
            asyncio.run_coroutine_threadsafe(self._close_request(), self._loop)

    def _run(self):
        outcome = asyncio.run(self._capture())
        self._busy = False
        self.completed.emit(outcome)

    async def _capture(self):
        self._loop = asyncio.get_running_loop()
        try:
            return await self._capture_unchecked()
        except asyncio.TimeoutError:
            return CaptureFailed(f"screenshot selection timed out ({REQUEST_TIMEOUT}s)")
        except Exception as e:
            logging.error("[Snip] Portal capture failed: %s", e)
            return CaptureFailed(str(e))
        finally:
            self._loop = None

    async def _capture_unchecked(self):
        try:
            bus = await MessageBus(bus_type=BusType.SESSION).connect()
        except Exception as e:
            return BackendUnavailable(f"no session D-Bus for the XDG portal: {e}")
        self._bus = bus
        try:
            version = await self._screenshot_version(bus)
            if not isinstance(version, int):
                return version

            response = asyncio.get_running_loop().create_future()

            def on_message(message):
                if (
                    message.message_type == MessageType.SIGNAL
                    and message.interface == REQUEST_INTERFACE
                    and message.member == "Response"
                    and not response.done()
                ):
                    response.set_result(message.body)

            match = await bus.call(
                Message(
                    destination="org.freedesktop.DBus",
                    path="/org/freedesktop/DBus",
                    interface="org.freedesktop.DBus",
                    member="AddMatch",
                    signature="s",
                    body=[
                        "type='signal',"
                        f"interface='{REQUEST_INTERFACE}',member='Response',"
                        "path_namespace='/org/freedesktop/portal/desktop/request'"
                    ],
                )
            )
            if match.message_type == MessageType.ERROR:
                return CaptureFailed(f"could not subscribe to portal responses: {match.error_name}")
            bus.add_message_handler(on_message)

            options = {"handle_token": Variant("s", f"sniplens{next(self._tokens)}")}
            if version >= 3:
                targets = await self._available_targets(bus)
                if targets is not None and targets & AREA_TARGET:
                    options["target"] = Variant("u", AREA_TARGET)
                else:
                    options["interactive"] = Variant("b", True)
            else:
                options["interactive"] = Variant("b", True)

            reply = await bus.call(
                Message(
                    destination=PORTAL_SERVICE,
                    path=PORTAL_PATH,
                    interface=SCREENSHOT_INTERFACE,
                    member="Screenshot",
                    signature="sa{sv}",
                    body=["", options],
                )
            )
            if reply.message_type == MessageType.ERROR:
                if reply.error_name in UNAVAILABLE_ERRORS:
                    return BackendUnavailable(portal_unavailable_message())
                if reply.error_name == "org.freedesktop.portal.Error.NotAllowed":
                    return PermissionDenied("the desktop denied the screenshot request")
                return CaptureFailed(f"portal rejected the request: {reply.error_name}")

            self._request_path = reply.body[0]
            try:
                code, results = await asyncio.wait_for(response, REQUEST_TIMEOUT)
            except asyncio.TimeoutError:
                await self._close_request()
                raise
            finally:
                self._request_path = None

            # org.freedesktop.portal.Request: 0 carried out, 1 cancelled by the
            # user, 2 ended some other way - neither 1 nor 2 is a failure
            if code == 1:
                return Cancelled("dismissed in the portal selection")
            if code == 2:
                return Cancelled("portal selection ended without a screenshot")
            if code != 0:
                return CaptureFailed(f"portal returned response code {code}")

            uri = getattr(results.get("uri", ""), "value", results.get("uri", ""))
            path = QUrl(uri).toLocalFile()
            image = QImage(path)
            if image.isNull():
                return CaptureFailed(f"the portal screenshot could not be read: {uri}")
            with contextlib.suppress(OSError):
                os.remove(path)
            return Success(image)
        finally:
            self._bus = None
            bus.disconnect()

    async def _close_request(self):
        if self._bus is None or self._request_path is None:
            return
        await self._bus.call(
            Message(
                destination=PORTAL_SERVICE,
                path=self._request_path,
                interface=REQUEST_INTERFACE,
                member="Close",
            )
        )

    async def _screenshot_version(self, bus):
        """The Screenshot interface version, or the outcome explaining why it
        could not be read."""
        reply = await asyncio.wait_for(
            bus.call(
                Message(
                    destination=PORTAL_SERVICE,
                    path=PORTAL_PATH,
                    interface="org.freedesktop.DBus.Properties",
                    member="Get",
                    signature="ss",
                    body=[SCREENSHOT_INTERFACE, "version"],
                )
            ),
            5,
        )
        if reply.message_type == MessageType.ERROR:
            if reply.error_name in UNAVAILABLE_ERRORS:
                return BackendUnavailable(portal_unavailable_message())
            return CaptureFailed(
                f"could not read the portal Screenshot version: {reply.error_name}"
            )
        return getattr(reply.body[0], "value", reply.body[0])

    async def _available_targets(self, bus):
        reply = await asyncio.wait_for(
            bus.call(
                Message(
                    destination=PORTAL_SERVICE,
                    path=PORTAL_PATH,
                    interface="org.freedesktop.DBus.Properties",
                    member="Get",
                    signature="ss",
                    body=[SCREENSHOT_INTERFACE, "AvailableTargets"],
                )
            ),
            5,
        )
        if reply.message_type == MessageType.ERROR:
            return None
        return getattr(reply.body[0], "value", reply.body[0])
