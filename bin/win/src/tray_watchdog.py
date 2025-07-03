import os
import sys
import json
import atexit
import subprocess
import psutil
import time
import hashlib
import copykitten
from PIL import Image
from io import BytesIO
import requests
import threading
import webbrowser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

EXE_DIR = os.path.dirname(
    os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
)
EXIT_WATCHDOG = os.path.join(EXE_DIR, ".exit_watchdog")
SETTINGS_PATH = os.path.join(EXE_DIR, "settings.json")
LOCKFILE = os.path.join(EXE_DIR, ".tray_watchdog.lock")
LOG_FILE = os.path.join(EXE_DIR, "sniplens.log")


def singleton_lock():
    if os.path.exists(LOCKFILE):
        try:
            with open(LOCKFILE, "r") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                if "python" in proc.name().lower() and any(
                    "tray_watchdog.py" in part for part in proc.cmdline()
                ):
                    print(
                        "tray_watchdog.py is already running (PID {}). Exiting.".format(
                            pid
                        )
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


singleton_lock()
atexit.register(remove_lock)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

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
    with open(SETTINGS_PATH, "w") as f:
        json.dump(raw, f, indent=4)
except Exception as e:
    logging.error("Failed to set tray_ui_enabled to True on watchdog start: %s", e)


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


def tray_setting():
    try:
        with open(SETTINGS_PATH, "r") as f:
            raw = json.load(f)
        v = raw["tray_ui_enabled"]
        if isinstance(v, dict) and "value" in v:
            return bool(v["value"])
        return bool(v)
    except Exception:
        return True


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


def snippingtool_running():
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() in [
                "snippingtool.exe",
                "screenclippinghost.exe",
                "sniptool.exe",
                "snipandsketch.exe",
            ]:
                return True
        except Exception:
            continue
    return False


def md5_image(pixels):
    return hashlib.md5(pixels).hexdigest()


def grab_clipboard_image_and_hash():
    try:
        pixels, width, height = copykitten.paste_image()
        return md5_image(pixels), (pixels, width, height)
    except Exception:
        return None, None


def get_settings():
    try:
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def get_tray_status():
    raw = get_settings()
    val = raw.get("tray_status", 0)
    if isinstance(val, dict) and "value" in val:
        return int(val["value"])
    return int(val)


def update_settings(updates: dict, delete_keys: list = None):
    """Safely update settings, with an option to delete keys."""
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


def clipboard_monitor_loop():
    last_snip_running = False
    last_hash = get_settings().get("last_detected_image", "")
    while True:
        if os.path.exists(EXIT_WATCHDOG):
            break

        now_running = snippingtool_running()

        if last_snip_running and not now_running:
            logging.info("[SnippingTool] Detected close. Checking clipboard...")
            hash_val, image_data = grab_clipboard_image_and_hash()

            settings = get_settings()
            tray_snip_token = settings.get("tray_snip_token")
            is_tray_snip = bool(tray_snip_token)

            if is_tray_snip:
                logging.info(f"Consumed snip token: {tray_snip_token}")
                # Atomically consume the token by deleting it from settings
                update_settings({}, delete_keys=["tray_snip_token"])

            if hash_val and hash_val != last_hash:
                logging.info("[SnippingTool] New clipboard image found.")
                update_settings({"last_detected_image": hash_val})
                tray_status = get_tray_status()

                do_upload = tray_status == 2 or (tray_status == 1 and is_tray_snip)
                do_open_lens = do_upload

                if do_upload and image_data is not None:
                    pixels, width, height = image_data
                    img = Image.frombytes(
                        mode="RGBA", size=(width, height), data=pixels
                    )
                    with BytesIO() as output:
                        img.save(output, format="PNG")
                        output.seek(0)
                        files = {
                            "reqtype": (None, "fileupload"),
                            "time": (None, "1h"),
                            "fileToUpload": ("snip.png", output, "image/png"),
                        }
                        logging.info("[Litterbox] Uploading image...")
                        try:
                            response = requests.post(
                                "https://litterbox.catbox.moe/resources/internals/api.php",
                                files=files,
                                timeout=10,
                            )
                            if response.status_code == 200:
                                url = response.text.strip()
                                logging.info(f"[Litterbox] Upload success: {url}")
                                update_settings({"last_litterbox_url": url})
                                if do_open_lens:
                                    lens_url = (
                                        f"https://lens.google.com/uploadbyurl?url={url}"
                                    )
                                    logging.info(f"[Google Lens] Opening: {lens_url}")
                                    webbrowser.open_new_tab(lens_url)
                            else:
                                logging.error(
                                    f"[Litterbox] Upload failed with status: {response.status_code}"
                                )
                        except Exception as e:
                            logging.error(f"[Litterbox] Upload error: {e}")
                else:
                    logging.info(
                        "[SnippingTool] No upload or duplicate or not allowed."
                    )
            else:
                logging.info("[SnippingTool] No new image or duplicate.")

        last_snip_running = now_running
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


class SettingsHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.last_state = tray_setting()
        if self.last_state and not is_tray_running():
            launch_tray()
        elif not self.last_state and is_tray_running():
            kill_tray()

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


if __name__ == "__main__":
    if not is_tray_running():
        launch_tray()

    logging.info("[Watchdog] Starting background threads.")
    threading.Thread(target=clipboard_monitor_loop, daemon=True).start()
    threading.Thread(target=watchdog_tray_monitor, daemon=True).start()

    observer = Observer()
    event_handler = SettingsHandler()
    observer.schedule(event_handler, EXE_DIR, recursive=False)
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
        observer.stop()
        observer.join()
        logging.info("[Watchdog] Observer stopped. Exiting.")
