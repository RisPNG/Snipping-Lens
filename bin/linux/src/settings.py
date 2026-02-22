import json
import os
import sys
from typing import Any


SRC_DIR = os.path.dirname(
    os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
)
BIN_LINUX_DIR = os.path.abspath(os.path.join(SRC_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(BIN_LINUX_DIR, "..", ".."))

CONFIG_DIR = os.path.join(BIN_LINUX_DIR, "config")
LOG_DIR = os.path.join(BIN_LINUX_DIR, "logs")

SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")
LOG_FILE = os.path.join(LOG_DIR, "sniplens.log")

LOCKFILE_MAIN = os.path.join(SRC_DIR, ".sniplens.lock")
LOCKFILE_CONFIG = os.path.join(SRC_DIR, ".flet_config.lock")

ICON_PATH = os.path.abspath(
    os.path.join(BIN_LINUX_DIR, "..", "win", "assets", "sniplens.png")
)

SETUP_LINUX_SH = os.path.join(REPO_ROOT, "setup_linux.sh")

DEFAULT_SETTINGS_WRAPPED: dict[str, dict[str, Any]] = {
    "tray_status": {
        "value": 2,
        "description": "0=Pause, 1=Tray Only, 2=Always On",
    },
    "startup": {
        "value": 0,
        "description": "0=Off, 1=On",
    },
    "alternate_hotkey": {
        "value": "rctrl+ralt+s",
        "description": (
            "Global hotkey to start a snip (X11 only). "
            "Examples: 'rctrl+ralt+s', 'ctrl+shift+s'"
        ),
    },
}


def ensure_dirs() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


def _unwrap_value(value: Any, default: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    if value is None:
        return default
    return value


def _coerce_tray_status(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return int(DEFAULT_SETTINGS_WRAPPED["tray_status"]["value"])


def load_settings_raw() -> dict[str, Any]:
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_settings() -> dict[str, Any]:
    ensure_dirs()
    raw = load_settings_raw()
    needs_write = False

    tray_status = _coerce_tray_status(
        _unwrap_value(
            raw.get("tray_status"), DEFAULT_SETTINGS_WRAPPED["tray_status"]["value"]
        )
    )
    startup = _coerce_tray_status(
        _unwrap_value(raw.get("startup"), DEFAULT_SETTINGS_WRAPPED["startup"]["value"])
    )
    hotkey = str(
        _unwrap_value(
            raw.get("alternate_hotkey"),
            DEFAULT_SETTINGS_WRAPPED["alternate_hotkey"]["value"],
        )
        or ""
    ).strip()

    for key in DEFAULT_SETTINGS_WRAPPED:
        entry = raw.get(key)
        if not (isinstance(entry, dict) and "value" in entry):
            needs_write = True
            break

    settings = {
        "tray_status": tray_status,
        "startup": 1 if startup == 1 else 0,
        "alternate_hotkey": hotkey,
    }

    # Ensure file exists with our expected schema (preserve unknown keys).
    if needs_write or not os.path.exists(SETTINGS_PATH):
        save_settings(settings)
    return settings


def save_settings(values: dict[str, Any]) -> None:
    ensure_dirs()
    raw = load_settings_raw()

    raw["tray_status"] = {
        "value": int(
            values.get(
                "tray_status", DEFAULT_SETTINGS_WRAPPED["tray_status"]["value"]
            )
        ),
        "description": DEFAULT_SETTINGS_WRAPPED["tray_status"]["description"],
    }
    raw["startup"] = {
        "value": 1 if int(values.get("startup", 0)) == 1 else 0,
        "description": DEFAULT_SETTINGS_WRAPPED["startup"]["description"],
    }
    raw["alternate_hotkey"] = {
        "value": str(
            values.get(
                "alternate_hotkey",
                DEFAULT_SETTINGS_WRAPPED["alternate_hotkey"]["value"],
            )
            or ""
        ).strip(),
        "description": DEFAULT_SETTINGS_WRAPPED["alternate_hotkey"]["description"],
    }

    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=4)

