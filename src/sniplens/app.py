import logging
import os
import signal
import socket
import subprocess
import sys
import webbrowser

from PySide6.QtCore import QFileSystemWatcher, QObject, QSocketNotifier, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from sniplens import APP_NAME, __version__, paths
from sniplens.capture import Cancelled, Success, create_capture_service
from sniplens.hotkey import HotkeyController
from sniplens.images import image_hash, png_bytes
from sniplens.lens import GOOGLE_LENS_URL, LensSearchService
from sniplens.logging_setup import setup_logging
from sniplens.settings import ALWAYS_ON, PAUSED, TRAY_ONLY, SettingsStore
from sniplens.shortcuts import ensure_integration_entries
from sniplens.tray import TrayController

SINGLE_INSTANCE_NAME = "snipping-lens"

# the keys Windows itself binds to the Snipping Tool; watching them is how a
# snip the user started without us still arms a capture transaction
SYSTEM_SNIP_HOTKEYS = ("win+shift+s", "printscreen")


class ApplicationCore:
    """The authoritative application state; every other component reads this
    and none of them keeps a copy of its own."""

    def __init__(self, store):
        self.store = store
        self.values = store.load()

    def reload(self):
        self.values = self.store.load()

    @property
    def tray_status(self):
        return self.values.get("tray_status", ALWAYS_ON)

    @property
    def startup_enabled(self):
        return self.values.get("startup", 0) == 1

    @property
    def app_menu_enabled(self):
        return self.values.get("app_menu", 0) == 1

    @property
    def alternate_hotkey(self):
        return self.values.get("alternate_hotkey", "")

    @property
    def alternate_hotkey_bypass(self):
        return bool(self.values.get("alternate_hotkey_bypass", True))

    @property
    def last_detected_image(self):
        return self.values.get("last_detected_image", "")

    def remember_detected_image(self, digest):
        self.values["last_detected_image"] = digest
        self.store.save({"last_detected_image": digest})


class ApplicationController(QObject):
    """Owns the application lifecycle; tray and hotkey only forward commands
    here, and close-window/quit stay distinct from real shutdown."""

    # emitted from any thread (pynput listener, tray), handled on the GUI
    # thread where the Qt capture backends must run
    _snipRequested = Signal(bool)
    _systemSnipDetected = Signal()

    def __init__(self, core, capture, lens):
        super().__init__()
        self._core = core
        self._capture = capture
        self._lens = lens
        self._lens.searchFinished.connect(self._open_lens)
        self._snipRequested.connect(self._handle_snip_request)
        self._systemSnipDetected.connect(self._handle_system_snip)
        self._tray = None
        self._hotkey = HotkeyController()
        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_settings_dir_changed)
        self._watcher.fileChanged.connect(self._on_settings_file_changed)
        self._instance_server = None
        self._wakeup_reader = None
        self._wakeup_writer = None
        self._config_process = None
        self._pending_from_app_trigger = True
        self._quitting = False

    def attach_tray(self, tray):
        self._tray = tray

    def start(self):
        self._watcher.addPath(paths.CONFIG_DIR)
        if os.path.exists(paths.SETTINGS_PATH):
            self._watcher.addPath(paths.SETTINGS_PATH)
        self._capture.completed.connect(self._on_snip_completed)
        self._hotkey.reconfigure(self._hotkeys())
        ensure_integration_entries(
            self._core.startup_enabled, self._core.app_menu_enabled
        )
        self._listen_for_instances()
        self._install_signal_handlers()

    def request_snip(self, from_app_trigger=True):
        self._snipRequested.emit(from_app_trigger)

    def notify_system_snip(self):
        self._systemSnipDetected.emit()

    def open_config_window(self):
        if self._config_process is not None and self._config_process.poll() is None:
            logging.info("Config window already running.")
            return
        logging.info("Launching Snipping Lens main window.")
        # the window closes itself once this pipe does, so it never outlives
        # the app - whether the app quits or dies
        self._config_process = subprocess.Popen(
            [sys.executable, paths.CONFIG_WINDOW_SCRIPT], stdin=subprocess.PIPE
        )

    def quit(self):
        if self._quitting:
            return
        self._quitting = True
        logging.info("Shutting down %s.", APP_NAME)
        self._watcher.removePaths(self._watcher.files() + self._watcher.directories())
        self._hotkey.stop()
        self._capture.stop()
        self._lens.stop()
        if self._config_process is not None:
            self._config_process.stdin.close()
        if self._tray is not None:
            self._tray.shutdown()
        if self._wakeup_writer is not None:
            signal.set_wakeup_fd(-1)
            self._wakeup_reader.close()
            self._wakeup_writer.close()
        if self._instance_server is not None:
            self._instance_server.close()
            QLocalServer.removeServer(SINGLE_INSTANCE_NAME)
        QApplication.quit()

    def _hotkeys(self):
        hotkeys = {}
        if self._core.alternate_hotkey:
            hotkeys[self._core.alternate_hotkey] = lambda: self.request_snip(
                from_app_trigger=self._core.alternate_hotkey_bypass
            )
        if paths.IS_WINDOWS:
            for combination in SYSTEM_SNIP_HOTKEYS:
                hotkeys[combination] = self.notify_system_snip
        return hotkeys

    def _handle_snip_request(self, from_app_trigger):
        if not paths.IS_WINDOWS:
            status = self._core.tray_status
            if status == PAUSED:
                logging.info("[Snip] Paused, skipping snip.")
                return
            if status == TRAY_ONLY and not from_app_trigger:
                logging.info("[Snip] Tray Only mode but snip not triggered from the app, skipping.")
                return
        self._pending_from_app_trigger = from_app_trigger
        self._capture.request_region()

    def _handle_system_snip(self):
        if self._core.tray_status == PAUSED:
            logging.info("[Snip] Paused, ignoring the system snip.")
            return
        self._pending_from_app_trigger = False
        self._capture.arm_for_system_snip()

    def _on_snip_completed(self, outcome):
        if self._quitting:
            return
        if isinstance(outcome, Cancelled):
            logging.info("[Snip] Capture cancelled: %s", outcome.reason)
            return
        if not isinstance(outcome, Success):
            logging.error("[Snip] Capture failed: %s", outcome.message)
            return
        if paths.IS_WINDOWS:
            # the Windows clipboard is the transport, so the same capture can be
            # announced more than once; Linux backends hand the image straight over
            digest = image_hash(outcome.image)
            if digest == self._core.last_detected_image:
                logging.info("[Snip] Duplicate clipboard image, skipping search.")
                return
            self._core.remember_detected_image(digest)
        else:
            QGuiApplication.clipboard().setImage(outcome.image)
        if self._should_search(self._pending_from_app_trigger):
            self._lens.search(png_bytes(outcome.image))
        else:
            logging.info("[Snip] Search skipped by the activation mode.")

    def _should_search(self, from_app_trigger):
        status = self._core.tray_status
        return status == ALWAYS_ON or (status == TRAY_ONLY and from_app_trigger)

    def _open_lens(self, url):
        lens_url = GOOGLE_LENS_URL.format(url)
        logging.info("[Google Lens] Opening: %s", lens_url)
        webbrowser.open_new_tab(lens_url)

    def _on_settings_dir_changed(self, _path):
        if os.path.exists(paths.SETTINGS_PATH) and paths.SETTINGS_PATH not in self._watcher.files():
            self._watcher.addPath(paths.SETTINGS_PATH)
        self._reload_settings()

    def _on_settings_file_changed(self, path):
        # settings are saved by replacing the file, which drops the old inode
        # out of the watch list
        if os.path.exists(path):
            self._watcher.addPath(path)
        self._reload_settings()

    def _reload_settings(self):
        self._core.reload()
        self._hotkey.reconfigure(self._hotkeys())

    def _listen_for_instances(self):
        server = QLocalServer(self)
        if not server.listen(SINGLE_INSTANCE_NAME):
            # only a socket left behind by a crashed instance can block this;
            # a live one was already ruled out by _signal_existing_instance
            QLocalServer.removeServer(SINGLE_INSTANCE_NAME)
            if not server.listen(SINGLE_INSTANCE_NAME):
                logging.warning("Single-instance listener unavailable: %s", server.errorString())
                return
        server.newConnection.connect(self._on_instance_connection)
        self._instance_server = server

    def _on_instance_connection(self):
        connection = self._instance_server.nextPendingConnection()
        if connection is None:
            return
        connection.setParent(self._instance_server)

        def read_activation():
            if b"activate" in bytes(connection.readAll()):
                self.open_config_window()
                connection.disconnectFromServer()

        connection.readyRead.connect(read_activation)
        # the activation byte usually arrives together with the connection,
        # before readyRead can be connected
        read_activation()

    def _install_signal_handlers(self):
        # a socketpair rather than a pipe: on Windows os.set_blocking does not
        # exist and QSocketNotifier is serviced by WSAAsyncSelect, which only
        # accepts sockets
        self._wakeup_reader, self._wakeup_writer = socket.socketpair()
        self._wakeup_reader.setblocking(False)
        self._wakeup_writer.setblocking(False)
        signal.set_wakeup_fd(self._wakeup_writer.fileno())
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda _signum, _frame: None)
        # parented to the controller so it lives as long as the application
        notifier = QSocketNotifier(
            self._wakeup_reader.fileno(), QSocketNotifier.Type.Read, self
        )
        notifier.activated.connect(self._on_signal_received)

    def _on_signal_received(self):
        self._wakeup_reader.recv(256)
        self.quit()


def _signal_existing_instance():
    client = QLocalSocket()
    client.connectToServer(SINGLE_INSTANCE_NAME)
    if not client.waitForConnected(1000):
        return False
    client.write(b"activate")
    client.waitForBytesWritten(1000)
    logging.info("%s is already running, signaling it instead.", APP_NAME)
    return True


def run():
    setup_logging()
    os.makedirs(paths.CONFIG_DIR, exist_ok=True)
    logging.info("%s %s starting.", APP_NAME, __version__)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)

    if _signal_existing_instance():
        return 0

    core = ApplicationCore(SettingsStore())
    lens = LensSearchService()
    lens.start()
    controller = ApplicationController(core, create_capture_service(app), lens)

    tray = TrayController(
        controller, paths.TRAY_ICON_PATH, snip_on_left_click=paths.IS_WINDOWS
    )
    controller.attach_tray(tray)
    controller.start()
    tray.show()

    exit_code = app.exec()
    controller.quit()
    return exit_code
