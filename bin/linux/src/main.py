import atexit
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser

import psutil
from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from settings import (
    ICON_PATH,
    LOCKFILE_CONFIG,
    LOCKFILE_MAIN,
    LOG_FILE,
    SETTINGS_PATH,
    load_settings,
)

try:
    from pynput import keyboard

    HOTKEY_AVAILABLE = True
except Exception:
    HOTKEY_AVAILABLE = False


EXE_DIR = os.path.dirname(
    os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
)


def singleton_lock() -> None:
    if os.path.exists(LOCKFILE_MAIN):
        try:
            with open(LOCKFILE_MAIN, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                cmdline = proc.cmdline()
                if "python" in proc.name().lower() and any(
                    part.endswith("main.py") for part in cmdline
                ):
                    print(
                        f"Snipping Lens (linux) is already running (PID {pid}). Exiting."
                    )
                    sys.exit(0)
        except Exception:
            pass
        try:
            os.remove(LOCKFILE_MAIN)
        except Exception:
            pass
    with open(LOCKFILE_MAIN, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))


def remove_lock() -> None:
    try:
        if os.path.exists(LOCKFILE_MAIN):
            os.remove(LOCKFILE_MAIN)
            logging.info("main.py lockfile removed on exit.")
    except Exception:
        pass


def signal_handler(signum, frame) -> None:
    logging.info("Received signal %s, cleaning up...", signum)
    remove_lock()
    sys.exit(0)


def open_config_window() -> None:
    if os.path.exists(LOCKFILE_CONFIG):
        try:
            with open(LOCKFILE_CONFIG, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                logging.info("Config window already running (PID %s).", pid)
                return
        except Exception:
            pass
        try:
            os.remove(LOCKFILE_CONFIG)
        except Exception:
            pass

    logging.info("Launching config window.")
    subprocess.Popen([sys.executable, os.path.join(EXE_DIR, "config_window.py")])


def terminate_config_window(timeout_s: float = 2.0) -> None:
    if not os.path.exists(LOCKFILE_CONFIG):
        return
    try:
        with open(LOCKFILE_CONFIG, "r", encoding="utf-8") as f:
            pid = int(f.read().strip())
    except Exception:
        return

    if not psutil.pid_exists(pid):
        try:
            os.remove(LOCKFILE_CONFIG)
        except Exception:
            pass
        return

    try:
        proc = psutil.Process(pid)
        cmdline = " ".join(proc.cmdline() or [])
        if "config_window.py" not in cmdline:
            return

        logging.info("Terminating config window (PID %s)...", pid)
        proc.terminate()
        try:
            proc.wait(timeout=timeout_s)
        except psutil.TimeoutExpired:
            logging.info("Config window did not exit in time; killing (PID %s)...", pid)
            proc.kill()
            try:
                proc.wait(timeout=1.0)
            except Exception:
                pass
    except Exception as e:
        logging.error("Failed to terminate config window: %s", e)
    finally:
        try:
            if not psutil.pid_exists(pid) and os.path.exists(LOCKFILE_CONFIG):
                os.remove(LOCKFILE_CONFIG)
        except Exception:
            pass


def session_type() -> str:
    return str(os.environ.get("XDG_SESSION_TYPE") or "").strip().lower()


def _run_command(
    args: list[str], timeout_s: int | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )


def take_screenshot_and_upload() -> str | None:
    if session_type() not in ("", "x11"):
        logging.warning(
            "Detected session type '%s'. X11 is required for maim -s. Wayland not supported yet.",
            session_type(),
        )
        return None

    tmp_path = f"/tmp/snipping-lens-{os.getpid()}.png"

    try:
        maim = _run_command(["maim", "-s", tmp_path])
        if maim.returncode != 0:
            logging.info(
                "[maim] Cancelled or failed (code %s): %s",
                maim.returncode,
                (maim.stderr or "").strip(),
            )
            return None

        curl = _run_command(
            [
                "curl",
                "-fsS",
                "-F",
                "reqtype=fileupload",
                "-F",
                "time=1h",
                "-F",
                f"fileToUpload=@{tmp_path}",
                "https://litterbox.catbox.moe/resources/internals/api.php",
            ],
            timeout_s=30,
        )
        if curl.returncode != 0:
            logging.error(
                "[curl] Upload failed (code %s): %s",
                curl.returncode,
                (curl.stderr or "").strip(),
            )
            return None

        url = (curl.stdout or "").strip()
        if not url.startswith("http"):
            logging.error("[curl] Unexpected response: %r", url)
            return None

        logging.info("[Litterbox] Upload success: %s", url)
        return url
    except FileNotFoundError as e:
        logging.error("Missing dependency: %s", e)
        return None
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def open_google_lens(image_url: str) -> None:
    encoded = urllib.parse.quote(image_url, safe="")
    lens_url = f"https://lens.google.com/uploadbyurl?url={encoded}"
    logging.info("[Google Lens] Opening: %s", lens_url)
    webbrowser.open_new_tab(lens_url)


def to_pynput_hotkeys(hotkey: str) -> list[str]:
    parts = [p.strip().lower() for p in (hotkey or "").split("+") if p.strip()]
    if not parts:
        return []

    mapped: list[str] = []
    for part in parts:
        if part in ("ctrl", "control"):
            mapped.append("<ctrl>")
        elif part in ("rctrl", "ctrl_r", "rightctrl", "rightcontrol"):
            mapped.append("<ctrl_r>")
        elif part in ("lctrl", "ctrl_l", "leftctrl", "leftcontrol"):
            mapped.append("<ctrl_l>")
        elif part == "alt":
            mapped.append("<alt>")
        elif part in ("ralt", "alt_r", "rightalt"):
            mapped.append("<alt_r>")
        elif part in ("altgr", "alt_gr", "raltgr", "rightaltgr"):
            mapped.append("<alt_gr>")
        elif part in ("lalt", "alt_l", "leftalt"):
            mapped.append("<alt_l>")
        elif part == "shift":
            mapped.append("<shift>")
        elif part in ("rshift", "shift_r", "rightshift"):
            mapped.append("<shift_r>")
        elif part in ("lshift", "shift_l", "leftshift"):
            mapped.append("<shift_l>")
        elif part in ("win", "cmd", "meta", "super"):
            mapped.append("<cmd>")
        elif part in ("space",):
            mapped.append("space")
        elif part in ("esc", "escape"):
            mapped.append("esc")
        elif part in ("enter", "return"):
            mapped.append("enter")
        else:
            mapped.append(part)

    # De-dupe while preserving order.
    seen: set[str] = set()
    mapped_unique = []
    for p in mapped:
        if p not in seen:
            mapped_unique.append(p)
            seen.add(p)

    primary = "+".join(mapped_unique)
    variants = [primary]

    # On many Linux layouts, the physical "Right Alt" is "AltGr". Register both.
    if "<alt_r>" in primary:
        variants.append(primary.replace("<alt_r>", "<alt_gr>"))
    elif "<alt_gr>" in primary:
        variants.append(primary.replace("<alt_gr>", "<alt_r>"))

    # De-dupe variants.
    out: list[str] = []
    for v in variants:
        if v and v not in out:
            out.append(v)
    return out


class HotkeyManager:
    def __init__(self, on_trigger):
        self._on_trigger = on_trigger
        self._listener = None
        self._current: tuple[str, ...] = ()

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            self._current = ()

    def set_hotkey(self, hotkey: str, enabled: bool) -> None:
        if not HOTKEY_AVAILABLE:
            return

        desired = tuple(to_pynput_hotkeys(hotkey) if enabled else [])
        if desired == self._current:
            return

        self.stop()

        if not desired:
            logging.info("[Hotkey] Disabled.")
            return

        try:
            self._listener = keyboard.GlobalHotKeys(
                {hk: self._on_trigger for hk in desired}
            )
            self._listener.start()
            self._current = desired
            logging.info("[Hotkey] Listening on: %s", ", ".join(desired))
        except Exception as e:
            logging.error(
                "[Hotkey] Failed to set hotkey '%s': %s",
                "+".join(hotkey.split("+")),
                e,
            )
            self.stop()


class SnipRunner:
    def __init__(self):
        self._lock = threading.Lock()

    def trigger(self, source: str) -> None:
        if not self._lock.acquire(blocking=False):
            logging.info("[Snip] Ignored (%s): already running.", source)
            return

        def _work():
            try:
                logging.info("[Snip] Triggered by: %s", source)
                url = take_screenshot_and_upload()
                if url:
                    open_google_lens(url)
            except Exception as e:
                logging.error("[Snip] Error: %s", e)
            finally:
                try:
                    self._lock.release()
                except Exception:
                    pass

        threading.Thread(target=_work, daemon=True).start()


class TrayApp(QObject):
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self._settings_mtime = 0.0
        self.settings = load_settings()
        self.tray_status = int(self.settings.get("tray_status", 2))
        self.hotkey_spec = str(self.settings.get("alternate_hotkey", "")).strip()

        self.snip_runner = SnipRunner()
        self.hotkey = HotkeyManager(lambda: self.on_hotkey())
        self.hotkey.set_hotkey(self.hotkey_spec, enabled=self.tray_status == 2)

        self.tray_icon = QSystemTrayIcon(QIcon(ICON_PATH))
        self.tray_icon.setToolTip("Snipping Lens")
        self.tray_icon.activated.connect(self.icon_clicked)

        self.menu = QMenu()
        self.snip_action = QAction("Snip Now")
        self.snip_action.triggered.connect(lambda: self.maybe_snip("menu"))
        self.menu.addAction(self.snip_action)

        self.config_action = QAction("Open App")
        self.config_action.triggered.connect(open_config_window)
        self.menu.addAction(self.config_action)

        self.quit_action = QAction("Exit")
        self.quit_action.triggered.connect(self.exit_app)
        self.menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()
        logging.info("Tray icon shown.")

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.reload_settings_if_changed)
        self.timer.start()

    def icon_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.maybe_snip("tray")

    def on_hotkey(self):
        self.maybe_snip("hotkey")

    def maybe_snip(self, source: str) -> None:
        if self.tray_status == 0:
            logging.info("[Snip] Ignored (%s): paused.", source)
            return
        if self.tray_status == 1 and source != "tray" and source != "menu":
            logging.info("[Snip] Ignored (%s): tray-only mode.", source)
            return
        self.snip_runner.trigger(source)

    def reload_settings_if_changed(self) -> None:
        try:
            st = os.stat(SETTINGS_PATH)
            if st.st_mtime <= self._settings_mtime:
                return
            self._settings_mtime = st.st_mtime
        except FileNotFoundError:
            # load_settings() will recreate it.
            self._settings_mtime = time.time()
        except Exception:
            return

        try:
            new_settings = load_settings()
        except Exception as e:
            logging.error("Failed to reload settings: %s", e)
            return

        self.settings = new_settings
        self.tray_status = int(new_settings.get("tray_status", 2))
        self.hotkey_spec = str(new_settings.get("alternate_hotkey", "")).strip()
        self.hotkey.set_hotkey(self.hotkey_spec, enabled=self.tray_status == 2)

    def exit_app(self) -> None:
        terminate_config_window()
        try:
            self.hotkey.stop()
        except Exception:
            pass
        try:
            self.tray_icon.hide()
        except Exception:
            pass
        remove_lock()
        self.app.quit()

    def run(self) -> None:
        try:
            self.app.exec()
        finally:
            try:
                self.hotkey.stop()
            except Exception:
                pass
            remove_lock()


def setup_logging() -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


if __name__ == "__main__":
    singleton_lock()
    atexit.register(remove_lock)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    setup_logging()
    TrayApp().run()

