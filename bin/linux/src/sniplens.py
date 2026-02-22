import os
import sys
import json
import subprocess
import logging
import atexit
import uuid
import signal

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

# Support both AppIndicator3 (Ubuntu/older) and AyatanaAppIndicator3 (Debian/newer)
try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3
except ValueError:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3

EXE_DIR = os.path.dirname(os.path.abspath(__file__))
EXIT_WATCHDOG = os.path.join(EXE_DIR, ".exit_watchdog")
DO_SNIP_TRIGGER = os.path.join(EXE_DIR, ".do_snip")
SETTINGS_PATH = os.path.abspath(
    os.path.join(EXE_DIR, "..", "config", "settings.json")
)
LOCKFILE_APP = os.path.join(EXE_DIR, ".flet_config.lock")
LOCKFILE = os.path.join(EXE_DIR, ".sniplens.lock")
LOG_FILE = os.path.abspath(os.path.join(EXE_DIR, "..", "logs", "sniplens.log"))
ICON_PATH = os.path.abspath(os.path.join(EXE_DIR, "..", "assets", "sniplens.png"))

# Path to the venv Python (used to launch config_window.py which needs venv deps)
VENV_PYTHON = os.path.abspath(
    os.path.join(EXE_DIR, "..", "..", "..", "int", "linux", "venv", "bin", "python")
)


def _read_pid(path):
    """Read a PID from a lockfile and check if it's alive."""
    try:
        with open(path, "r") as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # Check if process exists (doesn't actually kill)
        return pid
    except (OSError, ValueError):
        return None


def singleton_lock():
    if os.path.exists(LOCKFILE):
        pid = _read_pid(LOCKFILE)
        if pid is not None:
            # Check if it's actually sniplens.py by reading /proc/PID/cmdline
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmdline = f.read().decode("utf-8", errors="replace")
                if "sniplens.py" in cmdline:
                    print(
                        "sniplens.py is already running (PID {}). Exiting.".format(pid)
                    )
                    sys.exit(0)
            except (OSError, IOError):
                pass
        try:
            os.remove(LOCKFILE)
        except OSError:
            pass
    with open(LOCKFILE, "w") as f:
        f.write(str(os.getpid()))


def remove_lock():
    try:
        if os.path.exists(LOCKFILE):
            os.remove(LOCKFILE)
            logging.info("sniplens.py lockfile removed on exit.")
    except Exception:
        pass


def signal_handler(signum, frame):
    logging.info(f"Received signal {signum}, cleaning up...")
    remove_lock()
    Gtk.main_quit()


singleton_lock()
atexit.register(remove_lock)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def update_settings(updates: dict):
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


def open_config_window():
    if os.path.exists(LOCKFILE_APP):
        pid = _read_pid(LOCKFILE_APP)
        if pid is not None:
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmdline = f.read().decode("utf-8", errors="replace")
                if "config_window.py" in cmdline:
                    logging.info("Config window already running.")
                    return
            except (OSError, IOError):
                pass
        try:
            os.remove(LOCKFILE_APP)
        except OSError:
            pass

    # Use the venv Python for config_window (it needs flet and other pip deps)
    python = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
    logging.info("Launching Snipping Lens config window.")
    subprocess.Popen([python, os.path.join(EXE_DIR, "config_window.py")])


def trigger_snip(_=None):
    """Signal the watchdog to perform a snip (from tray click)."""
    try:
        logging.info("Tray snip triggered: preparing for tray-based snip.")
        token = str(uuid.uuid4())
        update_settings({"tray_snip_token": token})
        logging.info(f"Generated snip token: {token}")

        with open(DO_SNIP_TRIGGER, "w") as f:
            f.write("snip")
        logging.info("Snip trigger file written.")
    except Exception as e:
        logging.error(f"Failed to trigger snip: {e}")


def exit_app(_=None):
    """Exit the tray app and signal watchdog to shut down."""
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

    logging.info("Tray app exited by user.")
    remove_lock()
    Gtk.main_quit()


def build_menu():
    """Build the GTK menu for the AppIndicator."""
    menu = Gtk.Menu()

    item_snip = Gtk.MenuItem(label="Snip")
    item_snip.connect("activate", trigger_snip)
    menu.append(item_snip)

    item_open = Gtk.MenuItem(label="Open App")
    item_open.connect("activate", lambda _: open_config_window())
    menu.append(item_open)

    separator = Gtk.SeparatorMenuItem()
    menu.append(separator)

    item_exit = Gtk.MenuItem(label="Exit")
    item_exit.connect("activate", exit_app)
    menu.append(item_exit)

    menu.show_all()
    return menu


def main():
    indicator = AppIndicator3.Indicator.new(
        "snipping-lens",
        ICON_PATH if os.path.exists(ICON_PATH) else "applications-other",
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
    indicator.set_menu(build_menu())
    indicator.set_title("Snipping Lens")

    logging.info("Tray icon starting (AppIndicator3).")

    try:
        Gtk.main()
    finally:
        remove_lock()


if __name__ == "__main__":
    main()
