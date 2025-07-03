import os
import sys
import json
import subprocess
import psutil
import logging
import atexit
import uuid

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, QPoint

EXE_DIR = os.path.dirname(
    os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
)
EXIT_WATCHDOG = os.path.join(EXE_DIR, ".exit_watchdog")
SETTINGS_PATH = os.path.join(EXE_DIR, "settings.json")
LOCKFILE_APP = os.path.join(EXE_DIR, ".flet_config.lock")
LOCKFILE = os.path.join(EXE_DIR, ".sniplens.lock")
LOG_FILE = os.path.join(EXE_DIR, "sniplens.log")


def singleton_lock():
    if os.path.exists(LOCKFILE):
        try:
            with open(LOCKFILE, "r") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                if "python" in proc.name().lower() and any(
                    "sniplens.py" in part for part in proc.cmdline()
                ):
                    print(
                        "sniplens.py is already running (PID {}). Exiting.".format(pid)
                    )
                    sys.exit(0)
        except Exception:
            pass
        try:
            os.remove(LOCKFILE)
        except Exception:
            pass
    with open(LOCKFILE, "w") as f:
        f.write(str(os.getpid()))


def remove_lock():
    try:
        if os.path.exists(LOCKFILE):
            os.remove(LOCKFILE)
    except Exception:
        pass


singleton_lock()
atexit.register(remove_lock)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

DEFAULT_SETTINGS_WRAPPED = {
    "tray_ui_enabled": {"value": True, "description": "Enable or disable the tray UI"},
    "tray_status": {"value": 2, "description": "0=Pause, 1=Tray Only, 2=Always On"},
}

DEFAULT_SETTINGS = {k: v["value"] for k, v in DEFAULT_SETTINGS_WRAPPED.items()}


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def extract_values(settings_obj):
    out = {}
    for key, entry in settings_obj.items():
        if isinstance(entry, dict) and "value" in entry:
            val = entry["value"]
            if key == "tray_status":
                try:
                    val = int(val)
                except Exception:
                    val = 1
            out[key] = val
    return out


def validate_settings(raw):
    for key in ["tray_ui_enabled", "tray_status"]:
        if key not in raw:
            raise ValueError(f"Missing key: {key}")
        value_entry = raw[key]
        if not isinstance(value_entry, dict) or "value" not in value_entry:
            raise ValueError(f"Invalid format for key: {key}")
        value = value_entry["value"]
        if key == "tray_ui_enabled":
            if not isinstance(value, bool):
                raise ValueError(f"{key} must be a boolean")
        elif key == "tray_status":
            if not (
                isinstance(value, int) or (isinstance(value, str) and value.isdigit())
            ):
                raise ValueError(f"{key} must be an integer or digit-string")


def load_settings():
    try:
        with open(SETTINGS_PATH, "r") as f:
            raw = json.load(f)
        validate_settings(raw)
        settings = extract_values(raw)
        return {
            key: settings.get(key, DEFAULT_SETTINGS[key]) for key in DEFAULT_SETTINGS
        }
    except Exception:
        with open(SETTINGS_PATH, "w") as f:
            json.dump(DEFAULT_SETTINGS_WRAPPED, f, indent=4)
        python = sys.executable
        os.execl(python, python, *sys.argv)


def update_settings(updates: dict):
    """Safely update and merge settings, then save to disk."""
    try:
        try:
            with open(SETTINGS_PATH, "r") as f:
                raw = json.load(f)
        except Exception:
            raw = {}
        raw.update(updates)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(raw, f, indent=4)
    except Exception as e:
        logging.error("Failed to update settings: %s", e)


def open_flet_window():
    if os.path.exists(LOCKFILE_APP):
        try:
            with open(LOCKFILE_APP, "r") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                if "python" in proc.name().lower():
                    logging.info("Application window already running.")
                    return
        except Exception:
            pass
        try:
            os.remove(LOCKFILE_APP)
        except Exception:
            pass
    logging.info("Launching Snipping Lens main window.")
    subprocess.Popen([sys.executable, os.path.join(EXE_DIR, "config_window.py")])


class TrayApp(QObject):
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.settings = load_settings()

        icon_path = "sniplens.png"
        self.tray_icon = QSystemTrayIcon(QIcon(resource_path(icon_path)))
        self.tray_icon.setToolTip("Snipping Lens")
        self.tray_icon.activated.connect(self.icon_clicked)

        self.menu = QMenu()
        self.menu.setStyleSheet(
            """
            QMenu {
                background-color: #333333;
                color: white;
                border: 1px solid #555;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #555555;
            }
            QMenu::item[text="Exit"] {
                text-align: center;
                color: #ff6b6b;
                font-weight: bold;
            }
        """
        )
        self.config_action = QAction("Open App")
        self.config_action.triggered.connect(self.open_config)
        self.menu.addAction(self.config_action)
        self.quit_action = QAction("Exit")
        self.quit_action.triggered.connect(self.exit_app)
        self.menu.addAction(self.quit_action)
        self.tray_icon.setContextMenu(self.menu)

        self.tray_ui_enabled = self.settings.get("tray_ui_enabled", True)
        if self.tray_ui_enabled:
            self.tray_icon.show()
            logging.info("Tray icon shown.")
        else:
            self.tray_icon.hide()
            logging.info("Tray icon hidden.")

        self.last_tray_click_pos = QPoint(0, 0)

    def icon_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            try:
                logging.info("Tray left-clicked: preparing for tray-based snip.")
                token = str(uuid.uuid4())
                update_settings({"tray_snip_token": token})
                logging.info(f"Generated snip token: {token}")

                logging.info("Launching Snipping Tool via ms-screenclip.")
                subprocess.Popen(["explorer.exe", "ms-screenclip:"])
            except Exception as e:
                logging.error(f"Failed to launch Snipping Tool: {e}")

    def open_config(self):
        open_flet_window()
        logging.info("Launched Snipping Lens main window.")

    def exit_app(self):
        try:
            with open(SETTINGS_PATH, "r") as f:
                raw = json.load(f)
            if "tray_ui_enabled" in raw:
                if isinstance(raw["tray_ui_enabled"], dict):
                    raw["tray_ui_enabled"]["value"] = False
                else:
                    raw["tray_ui_enabled"] = False
            else:
                raw["tray_ui_enabled"] = {
                    "value": False,
                    "description": "Enable or disable the tray UI",
                }
            with open(SETTINGS_PATH, "w") as f:
                json.dump(raw, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to set tray_ui_enabled to False on exit: {e}")
        with open(EXIT_WATCHDOG, "w") as f:
            f.write("exit")
        self.tray_icon.hide()
        logging.info("Tray app exited by user.")
        os._exit(0)

    def run(self):
        self.app.exec()


if __name__ == "__main__":
    TrayApp().run()
