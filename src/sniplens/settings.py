import json
import logging
import os
import time

from sniplens import paths

# Windows will not replace a file another process has open, nor open one that
# is being replaced. The main app and the config window both read and replace
# the settings file, so each briefly waits out the other.
SHARING_RETRY_ATTEMPTS = 50
SHARING_RETRY_DELAY = 0.01

PAUSED = 0
TRAY_ONLY = 1
ALWAYS_ON = 2

DEFAULT_SETTINGS = {
    "tray_status": {
        "value": ALWAYS_ON,
        "description": "0=Pause, 1=Tray Only, 2=Always On",
    },
    "startup": {
        "value": 0,
        "description": "0=Off, 1=On",
    },
    "alternate_hotkey": {
        "value": "" if paths.IS_WINDOWS else "alt+ctrl+\\",
        "description": "Hotkey to trigger a snip (e.g., 'ctrl+shift+s')",
    },
    "alternate_hotkey_bypass": {
        "value": True,
        "description": "Allow the alternate hotkey to perform an image search in Tray Only mode.",
    },
    "last_detected_image": {
        "value": "",
        "description": "MD5 of the last clipboard image that was searched.",
    },
}
if not paths.IS_WINDOWS:
    DEFAULT_SETTINGS["app_menu"] = {
        "value": 0,
        "description": "0=Off, 1=On",
    }


def _coerce(key, value):
    if key in ("tray_status", "startup", "app_menu"):
        return int(value)
    if key == "alternate_hotkey":
        return str(value).strip()
    if key == "alternate_hotkey_bypass":
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)
    return value


def _valid(key, value):
    if key == "tray_status":
        return isinstance(value, (int, str)) and str(value).strip("-").isdigit() and int(value) in (PAUSED, TRAY_ONLY, ALWAYS_ON)
    if key in ("startup", "app_menu"):
        return isinstance(value, (int, str)) and str(value).strip("-").isdigit() and int(value) in (0, 1)
    if key == "alternate_hotkey":
        return isinstance(value, str)
    if key == "alternate_hotkey_bypass":
        return isinstance(value, (bool, str, int))
    return True


def _wait_out_sharing_violation(operation, *args):
    for _ in range(SHARING_RETRY_ATTEMPTS - 1):
        try:
            return operation(*args)
        except PermissionError:
            time.sleep(SHARING_RETRY_DELAY)
    return operation(*args)


class SettingsStore:
    """Reader/writer for the wrapped {value, description} settings file shared
    between the main app and the config window process."""

    def __init__(self, path=paths.SETTINGS_PATH):
        self.path = path

    def load(self):
        try:
            with _wait_out_sharing_violation(open, self.path, "r") as f:
                raw = json.load(f)
        except FileNotFoundError:
            raw = {}
        except Exception:
            logging.warning("Settings file unreadable, using defaults: %s", self.path)
            raw = {}
        values = {}
        for key, entry in DEFAULT_SETTINGS.items():
            value = raw.get(key, entry["value"])
            if isinstance(value, dict) and "value" in value:
                value = value["value"]
            try:
                if not _valid(key, value):
                    raise ValueError(f"invalid {key}: {value!r}")
                values[key] = _coerce(key, value)
            except Exception:
                logging.warning("Invalid setting %s=%r, using default", key, value)
                values[key] = entry["value"]
        return values

    def save(self, values):
        updates = {}
        for key, value in values.items():
            if key not in DEFAULT_SETTINGS:
                continue
            updates[key] = {"value": value, "description": DEFAULT_SETTINGS[key]["description"]}
        try:
            raw = {}
            if os.path.exists(self.path):
                with _wait_out_sharing_violation(open, self.path, "r") as f:
                    # a file that exists but will not parse is another writer
                    # mid-write; merging into {} would drop every other setting
                    raw = json.load(f)
            raw.update(updates)
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            # written whole and moved into place so a reader -- the other
            # process, or our own settings watcher -- never sees a partial file
            temporary = f"{self.path}.tmp"
            with open(temporary, "w") as f:
                json.dump(raw, f, indent=4)
            _wait_out_sharing_violation(os.replace, temporary, self.path)
        except Exception as e:
            logging.error("Failed to update settings at %s, left unchanged: %s", self.path, e)
