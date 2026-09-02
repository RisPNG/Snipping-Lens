import logging
import os
import signal
import subprocess
import sys
import webbrowser

from PySide6.QtCore import QFileSystemWatcher, QObject, QSocketNotifier, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from sniplens import APP_NAME, __version__, paths
from sniplens.capture import (
    BackendUnavailable,
    Cancelled,
    CaptureFailed,
    PermissionDenied,
    Success,
    create_capture_service,
)
from sniplens.hotkey import HotkeyController
from sniplens.images import image_hash, png_bytes
from sniplens.lens import GOOGLE_LENS_URL, LensSearchService
from sniplens.logging_setup import setup_logging
from sniplens.settings import ALWAYS_ON, PAUSED, TRAY_ONLY, SettingsStore
from sniplens.shortcuts import ensure_integration_entries
from sniplens.tray import TrayController

SINGLE_INSTANCE_NAME = "snipping-lens"


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


class ApplicationController(QObject):
    """Owns the application lifecycle; tray and hotkey only forward commands
    here, and close-window/quit stay distinct from real shutdown."""

    # emitted from any thread (pynput listener, tray), handled on the GUI
    # thread where the Qt capture backends must run
    _snipRequested = Signal(bool)

    def __init__(self, core, capture, lens):
        super().__init__()
        self._core = core
        self._capture = capture
        self._lens = lens
        self._lens.searchFinished.connect(self._open_lens)
        self._snipRequested.connect(self._handle_snip_request)
        self._tray = None
        self._hotkey = HotkeyController(
            lambda: self.request_snip(from_app_trigger=self._core.alternate_hotkey_bypass)
        )
        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_settings_dir_changed)
        self._watcher.fileChanged.connect(self._on_settings_file_changed)
        self._config_process = None
        self._quitting = False

    def attach_tray(self, tray):
        self._tray = tray

    def start(self):
        self._watcher.addPath(paths.CONFIG_DIR)
        if os.path.exists(paths.SETTINGS_PATH):
            self._watcher.addPath(paths.SETTINGS_PATH)
        if paths.IS_WINDOWS:
            self._capture.completed.connect(self._on_snip_completed)
            self._capture.image_copied.connect(self._on_clipboard_image)
        else:
            self._capture.completed.connect(self._on_snip_completed)
        self._hotkey.reconfigure(self._core.alternate_hotkey)
        ensure_integration_entries(
            self._core.startup_enabled, self._core.app_menu_enabled
        )

    def request_snip(self, from_app_trigger=True):
        self._snipRequested.emit(from_app_trigger)

    def _handle_snip_request(self, from_app_trigger):
        if not paths.IS_WINDOWS:
            status = self._core.tray_status
            if status == PAUSED:
                logging.info("[Snip] Paused, skipping snip.")
                return
            if status == TRAY_ONLY and not from_app_trigger:
                logging.info("[Snip] Tray Only mode but snip not triggered from the app, skipping.")
                return
        self._capture.request_region(from_app_trigger=from_app_trigger)

    def open_config_window(self):
        if self._config_process is not None and self._config_process.poll() is None:
            logging.info("Config window already running.")
            return
        logging.info("Launching Snipping Lens main window.")
        self._config_process = subprocess.Popen(
            [sys.executable, paths.CONFIG_WINDOW_SCRIPT]
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
        if self._tray is not None:
            self._tray.shutdown()
        QApplication.quit()

    def _on_snip_completed(self, outcome):
        if isinstance(outcome, Success):
            if not paths.IS_WINDOWS:
                QGuiApplication.clipboard().setImage(outcome.image)
            if paths.IS_WINDOWS and self._already_seen(outcome.image):
                logging.info("[Snip] Duplicate clipboard image, skipping search.")
                return
            if self._should_search(outcome.from_app_trigger):
                self._lens.search(png_bytes(outcome.image))
            else:
                logging.info("[Snip] Search skipped by the activation mode.")
        elif isinstance(outcome, Cancelled):
            logging.info("[Snip] Capture cancelled: %s", outcome.reason)
        elif isinstance(outcome, (BackendUnavailable, CaptureFailed, PermissionDenied)):
            logging.error("[Snip] Capture failed: %s", outcome.message)

    def _on_clipboard_image(self, image):
        if self._core.tray_status != ALWAYS_ON:
            return
        if self._already_seen(image):
            return
        self._lens.search(png_bytes(image))

    def _should_search(self, from_app_trigger):
        status = self._core.tray_status
        return status == ALWAYS_ON or (status == TRAY_ONLY and from_app_trigger)

    def _already_seen(self, image):
        digest = image_hash(image)
        if digest == self._core.values.get("last_detected_image", ""):
            return True
        self._core.values["last_detected_image"] = digest
        self._core.store.save({"last_detected_image": digest})
        return False

    def _open_lens(self, url):
        lens_url = GOOGLE_LENS_URL.format(url)
        logging.info("[Google Lens] Opening: %s", lens_url)
        webbrowser.open_new_tab(lens_url)

    def _on_settings_dir_changed(self, _path):
        if os.path.exists(paths.SETTINGS_PATH) and paths.SETTINGS_PATH not in self._watcher.files():
            self._watcher.addPath(paths.SETTINGS_PATH)
        self._reload_settings()

    def _on_settings_file_changed(self, path):
        if os.path.exists(path):
            self._watcher.addPath(path)
        self._reload_settings()

    def _reload_settings(self):
        self._core.reload()
        self._hotkey.reconfigure(self._core.alternate_hotkey)


def _signal_existing_instance():
    client = QLocalSocket()
    client.connectToServer(SINGLE_INSTANCE_NAME)
    if not client.waitForConnected(1000):
        return False
    client.write(b"activate")
    client.waitForBytesWritten(1000)
    logging.info("%s is already running, signaling it instead.", APP_NAME)
    return True


def _listen_for_instances(controller):
    QLocalServer.removeServer(SINGLE_INSTANCE_NAME)
    server = QLocalServer()
    if not server.listen(SINGLE_INSTANCE_NAME):
        logging.warning("Single-instance listener unavailable: %s", server.errorString())
        return server

    def on_new_connection():
        connection = server.nextPendingConnection()
        if connection is None:
            return
        connection.setParent(server)

        def read_activation():
            if b"activate" in bytes(connection.readAll()):
                controller.open_config_window()
                connection.disconnectFromServer()

        connection.readyRead.connect(read_activation)
        # the activation byte usually arrives together with the connection,
        # before readyRead can be connected
        read_activation()

    server.newConnection.connect(on_new_connection)
    return server


def _install_signal_handlers(controller):
    read_fd, write_fd = os.pipe()
    os.set_blocking(write_fd, False)
    signal.set_wakeup_fd(write_fd)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda _signum, _frame: None)
    # parented to the controller so it lives as long as the application
    notifier = QSocketNotifier(read_fd, QSocketNotifier.Type.Read, controller)

    def wake_up():
        os.read(read_fd, 256)
        controller.quit()

    notifier.activated.connect(wake_up)


def run():
    setup_logging()
    os.makedirs(paths.CONFIG_DIR, exist_ok=True)
    os.makedirs(paths.LOGS_DIR, exist_ok=True)
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
    controller.start()

    tray = TrayController(
        controller, paths.TRAY_ICON_PATH, snip_on_left_click=paths.IS_WINDOWS
    )
    controller.attach_tray(tray)
    tray.show()

    server = _listen_for_instances(controller)
    _install_signal_handlers(controller)

    exit_code = app.exec()
    controller.quit()
    QLocalServer.removeServer(SINGLE_INSTANCE_NAME)
    return exit_code
