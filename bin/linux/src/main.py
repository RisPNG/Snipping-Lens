import os
import sys
import json
import atexit
import subprocess
import psutil
import time
import threading
import webbrowser
import requests
import logging
import signal

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import for hotkey functionality
try:
    from pynput import keyboard

    HOTKEY_AVAILABLE = True
except ImportError:
    HOTKEY_AVAILABLE = False
    logging.warning("pynput not available. Hotkey functionality disabled.")

EXE_DIR = os.path.dirname(
    os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
)
EXIT_WATCHDOG = os.path.join(EXE_DIR, ".exit_watchdog")
DO_SNIP_TRIGGER = os.path.join(EXE_DIR, ".do_snip")
SETTINGS_PATH = os.path.abspath(
    os.path.join(EXE_DIR, "..", "config", "settings.json")
)
LOCKFILE = os.path.join(EXE_DIR, ".tray_watchdog.lock")
LOG_FILE = os.path.abspath(os.path.join(EXE_DIR, "..", "logs", "sniplens.log"))
SCREENSHOT_PATH = "/tmp/sniplens_screenshot.png"

LITTERBOX_API = "https://litterbox.catbox.moe/resources/internals/api.php"
GOOGLE_LENS_URL = "https://lens.google.com/uploadbyurl?url={}"


def is_gnome_desktop():
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").strip()
    if not desktop:
        return False
    # XDG_CURRENT_DESKTOP is often colon-separated e.g. "ubuntu:GNOME"
    parts = [
        part.strip().upper()
        for part in desktop.replace(";", ":").split(":")
        if part.strip()
    ]
    return "GNOME" in parts


def upload_to_litterbox_requests(image_path: str):
    try:
        with open(image_path, "rb") as f:
            files = {
                "reqtype": (None, "fileupload"),
                "time": (None, "1h"),
                "fileToUpload": ("snip.png", f, "image/png"),
            }
            response = requests.post(LITTERBOX_API, files=files, timeout=30)

        if response.status_code == 200:
            return response.text.strip()

        logging.error(
            f"[Litterbox] Upload failed with status: {response.status_code}"
        )
        return None
    except Exception as e:
        logging.error(f"[Litterbox] Upload error: {e}")
        return None


def upload_to_litterbox_curl(image_path: str):
    try:
        result = subprocess.run(
            [
                "curl",
                "-sS",
                "-F",
                "reqtype=fileupload",
                "-F",
                "time=1h",
                "-F",
                f"fileToUpload=@{image_path}",
                LITTERBOX_API,
            ],
            timeout=30,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        logging.error("[Litterbox] curl is not installed. Falling back to requests.")
        return upload_to_litterbox_requests(image_path)
    except subprocess.TimeoutExpired:
        logging.error("[Litterbox] curl upload timed out (30s).")
        return None

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        logging.error(
            "[Litterbox] curl upload failed (exit code %d). %s",
            result.returncode,
            stderr,
        )
        return None

    url = (result.stdout or "").strip()
    if not url:
        logging.error("[Litterbox] curl upload returned an empty response.")
        return None
    return url


def singleton_lock():
    if os.path.exists(LOCKFILE):
        try:
            with open(LOCKFILE, "r") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                if "python" in proc.name().lower() and any(
                    "main.py" in part for part in proc.cmdline()
                ):
                    print(
                        "main.py is already running (PID {}). Exiting.".format(pid)
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
            logging.info("[Watchdog] Lockfile removed on clean exit.")
    except Exception:
        pass


def signal_handler(signum, frame):
    logging.info(f"[Watchdog] Received signal {signum}, cleaning up...")
    remove_lock()
    sys.exit(0)


singleton_lock()
atexit.register(remove_lock)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Global variable to hold the hotkey listener
hotkey_listener = None
current_hotkey = ""

# --- Settings helpers ---


def get_settings():
    try:
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def get_setting_value(key, default=None):
    raw = get_settings()
    val = raw.get(key, default)
    if isinstance(val, dict) and "value" in val:
        return val["value"]
    return val


def get_tray_status():
    val = get_setting_value("tray_status", 2)
    try:
        return int(val)
    except (ValueError, TypeError):
        return 2


def get_alternate_hotkey():
    val = get_setting_value("alternate_hotkey", "alt+ctrl+\\")
    return str(val).strip() if val else ""


def update_settings(updates: dict, delete_keys: list = None):
    try:
        try:
            with open(SETTINGS_PATH, "r") as f:
                raw = json.load(f)
        except Exception:
            raw = {}

        if delete_keys:
            for key in delete_keys:
                if key in raw:
                    del raw[key]

        raw.update(updates)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(raw, f, indent=4)
    except Exception as e:
        logging.error("Failed to update settings: %s", e)


def tray_setting():
    val = get_setting_value("tray_ui_enabled", True)
    return bool(val)


# --- Initialize settings on start ---
try:
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            raw = json.load(f)
    else:
        raw = {}

    if "tray_ui_enabled" in raw:
        if isinstance(raw["tray_ui_enabled"], dict):
            raw["tray_ui_enabled"]["value"] = True
        else:
            raw["tray_ui_enabled"] = True
    else:
        raw["tray_ui_enabled"] = {
            "value": True,
            "description": "Enable or disable the tray UI",
        }

    if "alternate_hotkey" not in raw:
        raw["alternate_hotkey"] = {
            "value": "alt+ctrl+\\",
            "description": "Hotkey to trigger snip (e.g., 'alt+ctrl+\\\\')",
        }

    if "tray_status" not in raw:
        raw["tray_status"] = {
            "value": 2,
            "description": "0=Pause, 1=Tray Only, 2=Always On",
        }

    if "startup" not in raw:
        raw["startup"] = {
            "value": 0,
            "description": "0=Off, 1=On",
        }

    if "app_menu" not in raw:
        raw["app_menu"] = {
            "value": 0,
            "description": "0=Off, 1=On",
        }

    with open(SETTINGS_PATH, "w") as f:
        json.dump(raw, f, indent=4)
except Exception as e:
    logging.error("Failed to initialize settings on watchdog start: %s", e)


# --- Snip logic ---


def do_snip(from_tray=False):
    """Capture a region screenshot, upload to Litterbox, and open Google Lens."""
    tray_status = get_tray_status()

    if tray_status == 0:
        logging.info("[Snip] Paused. Skipping snip.")
        return

    if tray_status == 1 and not from_tray:
        logging.info("[Snip] Tray Only mode but snip not from tray. Skipping.")
        return

    use_gnome = is_gnome_desktop()
    if use_gnome:
        logging.info(
            "[Snip] Detected GNOME via XDG_CURRENT_DESKTOP; using gnome-screenshot."
        )
    else:
        logging.info("[Snip] Using maim for region selection...")

    try:
        if use_gnome:
            result = subprocess.run(
                ["gnome-screenshot", "-a", "-f", SCREENSHOT_PATH],
                timeout=120,
            )
        else:
            result = subprocess.run(
                ["maim", "-s", SCREENSHOT_PATH],
                timeout=120,
            )
    except FileNotFoundError:
        if use_gnome:
            logging.error(
                "[Snip] gnome-screenshot is not installed. Please install gnome-screenshot."
            )
        else:
            logging.error("[Snip] maim is not installed. Please install maim.")
        return
    except subprocess.TimeoutExpired:
        logging.error("[Snip] Screenshot selection timed out (120s). Skipping.")
        return

    if result.returncode != 0:
        logging.info(
            "[Snip] Screenshot cancelled or failed (exit code %d).",
            result.returncode,
        )
        return

    if not os.path.exists(SCREENSHOT_PATH):
        logging.error("[Snip] Screenshot file not found after capture.")
        return

    # Upload to Litterbox
    logging.info("[Litterbox] Uploading image...")
    try:
        if use_gnome:
            url = upload_to_litterbox_curl(SCREENSHOT_PATH)
        else:
            url = upload_to_litterbox_requests(SCREENSHOT_PATH)

        if not url:
            return

        logging.info(f"[Litterbox] Upload success: {url}")
        update_settings({"last_litterbox_url": url})

        lens_url = GOOGLE_LENS_URL.format(url)
        logging.info(f"[Google Lens] Opening: {lens_url}")
        webbrowser.open_new_tab(lens_url)
    finally:
        # Clean up screenshot
        try:
            os.remove(SCREENSHOT_PATH)
        except OSError:
            pass


# --- Tray process management ---


def is_tray_running():
    current_pid = os.getpid()
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            pid = proc.info["pid"]
            if pid == current_pid:
                continue
            cmdline = proc.info["cmdline"]
            if cmdline and any("sniplens.py" in part for part in cmdline):
                return True
        except Exception:
            continue
    return False


def launch_tray():
    tray_path = os.path.join(EXE_DIR, "sniplens.py")
    subprocess.Popen([sys.executable, tray_path])


def kill_tray():
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"]
            if cmdline and any("sniplens.py" in part for part in cmdline):
                proc.kill()
        except Exception:
            continue


# --- Hotkey handling ---

# Mapping from our storage format to pynput string format
MODIFIER_TO_PYNPUT = {
    "ralt": "<alt_r>",
    "lalt": "<alt_l>",
    "alt": "<alt>",
    "rctrl": "<ctrl_r>",
    "lctrl": "<ctrl_l>",
    "ctrl": "<ctrl>",
    "rshift": "<shift_r>",
    "lshift": "<shift_l>",
    "shift": "<shift>",
    "rwin": "<cmd_r>",
    "lwin": "<cmd_l>",
    "win": "<cmd>",
    "meta": "<cmd>",
}


def setup_hotkey_listener():
    global hotkey_listener, current_hotkey

    if not HOTKEY_AVAILABLE:
        return

    new_hotkey = get_alternate_hotkey()

    if new_hotkey == current_hotkey:
        return

    # Stop existing listener
    if hotkey_listener:
        try:
            hotkey_listener.stop()
            logging.info(f"[Hotkey] Stopped listener for: {current_hotkey}")
        except Exception as e:
            logging.error(f"[Hotkey] Error stopping listener: {e}")
        hotkey_listener = None

    current_hotkey = new_hotkey

    if not new_hotkey:
        logging.info("[Hotkey] No hotkey set.")
        return

    try:
        hotkey_parts = new_hotkey.split("+")
        pynput_parts = []

        for part in hotkey_parts:
            part = part.strip().lower()
            if part in MODIFIER_TO_PYNPUT:
                pynput_parts.append(MODIFIER_TO_PYNPUT[part])
            else:
                pynput_parts.append(part)

        pynput_hotkey = "+".join(pynput_parts)

        def on_hotkey():
            logging.info("[Hotkey] Hotkey triggered, starting snip...")
            # Run snip in a separate thread so the hotkey listener isn't blocked
            threading.Thread(target=do_snip, args=(False,), daemon=True).start()

        hotkey_listener = keyboard.GlobalHotKeys({pynput_hotkey: on_hotkey})
        hotkey_listener.start()
        logging.info(f"[Hotkey] Set up listener for: {new_hotkey} -> {pynput_hotkey}")

    except Exception as e:
        logging.error(f"[Hotkey] Error setting up hotkey '{new_hotkey}': {e}")
        current_hotkey = ""


def cleanup_hotkey_listener():
    global hotkey_listener
    if hotkey_listener:
        try:
            hotkey_listener.stop()
            logging.info("[Hotkey] Cleaned up hotkey listener on exit.")
        except Exception as e:
            logging.error(f"[Hotkey] Error cleaning up hotkey listener: {e}")


# --- Monitor threads ---


def snip_trigger_monitor():
    """Watch for .do_snip trigger file from the tray process."""
    while True:
        if os.path.exists(EXIT_WATCHDOG):
            break

        if os.path.exists(DO_SNIP_TRIGGER):
            try:
                os.remove(DO_SNIP_TRIGGER)
            except OSError:
                pass

            # Check for tray_snip_token
            settings = get_settings()
            tray_snip_token = settings.get("tray_snip_token")
            is_tray_snip = bool(tray_snip_token)

            if is_tray_snip:
                logging.info(f"Consumed snip token: {tray_snip_token}")
                update_settings({}, delete_keys=["tray_snip_token"])

            do_snip(from_tray=is_tray_snip)

        time.sleep(0.2)


def watchdog_tray_monitor():
    missing_counter = 0
    check_interval = 1
    max_missing = 5

    while True:
        if os.path.exists(EXIT_WATCHDOG):
            break

        if not is_tray_running():
            missing_counter += 1
            if missing_counter >= max_missing:
                logging.info("[Watchdog] Tray app missing. Signaling watchdog exit.")
                with open(EXIT_WATCHDOG, "w") as f:
                    f.write("exit from tray monitor")
                break
        else:
            missing_counter = 0
        time.sleep(check_interval)


def hotkey_monitor_loop():
    last_check_time = 0
    check_interval = 2

    while True:
        if os.path.exists(EXIT_WATCHDOG):
            break

        current_time = time.time()
        if current_time - last_check_time >= check_interval:
            try:
                setup_hotkey_listener()
            except Exception as e:
                logging.error(f"[Hotkey] Error in hotkey monitor: {e}")
            last_check_time = current_time

        time.sleep(0.5)


class SettingsHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.last_state = tray_setting()
        if self.last_state and not is_tray_running():
            launch_tray()
        elif not self.last_state and is_tray_running():
            kill_tray()

        setup_hotkey_listener()

    def on_modified(self, event):
        if os.path.abspath(event.src_path) == os.path.abspath(SETTINGS_PATH):
            current_state = tray_setting()
            if current_state != self.last_state:
                if current_state:
                    if not is_tray_running():
                        launch_tray()
                else:
                    kill_tray()
                self.last_state = current_state

            setup_hotkey_listener()


if __name__ == "__main__":
    try:
        os.remove(EXIT_WATCHDOG)
    except OSError:
        pass
    try:
        os.remove(DO_SNIP_TRIGGER)
    except OSError:
        pass

    atexit.register(cleanup_hotkey_listener)

    if not is_tray_running():
        launch_tray()

    logging.info("[Watchdog] Starting background threads.")

    threading.Thread(target=snip_trigger_monitor, daemon=True).start()
    threading.Thread(target=watchdog_tray_monitor, daemon=True).start()

    if HOTKEY_AVAILABLE:
        threading.Thread(target=hotkey_monitor_loop, daemon=True).start()
        logging.info("[Watchdog] Hotkey monitoring enabled.")
    else:
        logging.info("[Watchdog] Hotkey monitoring disabled (pynput not available).")

    observer = Observer()
    event_handler = SettingsHandler()
    watch_dir = os.path.dirname(SETTINGS_PATH)
    observer.schedule(event_handler, watch_dir, recursive=False)
    observer.start()

    try:
        while not os.path.exists(EXIT_WATCHDOG):
            time.sleep(0.2)

        logging.info("[Watchdog] Exit signal received. Shutting down.")

        try:
            os.remove(EXIT_WATCHDOG)
        except OSError:
            pass

    except KeyboardInterrupt:
        logging.info("[Watchdog] Keyboard interrupt received. Shutting down.")
        with open(EXIT_WATCHDOG, "w") as f:
            f.write("exit from keyboard interrupt")

    finally:
        cleanup_hotkey_listener()
        observer.stop()
        observer.join()
        logging.info("[Watchdog] Observer stopped. Exiting.")
