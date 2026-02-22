import flet as ft
import os
import sys
import json
import asyncio
import subprocess
import logging

EXE_DIR = os.path.dirname(
    os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
)
LOCKFILE = os.path.join(EXE_DIR, ".flet_config.lock")
SETTINGS_PATH = os.path.abspath(
    os.path.join(EXE_DIR, "..", "config", "settings.json")
)
LOG_FILE = os.path.abspath(os.path.join(EXE_DIR, "..", "logs", "sniplens.log"))

# Detect the full path to setup_linux.sh (three levels up from src/)
SETUP_SCRIPT = os.path.abspath(os.path.join(EXE_DIR, "..", "..", "..", "setup_linux.sh"))
AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
DESKTOP_FILE = os.path.join(AUTOSTART_DIR, "snipping-lens-startup.desktop")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Known modifier keys for left/right distinction
MODIFIER_KEYS = {
    "control left": "lctrl",
    "control right": "rctrl",
    "alt left": "lalt",
    "alt right": "ralt",
    "shift left": "lshift",
    "shift right": "rshift",
    "meta left": "lwin",
    "meta right": "rwin",
}

# Flet key names that are generic modifiers (no left/right)
GENERIC_MODIFIER_NAMES = {"control", "alt", "shift", "meta", "cmd"}


def write_pid_lock():
    try:
        with open(LOCKFILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def remove_lock():
    try:
        if os.path.exists(LOCKFILE):
            os.remove(LOCKFILE)
    except Exception:
        pass


def load_settings():
    try:
        with open(SETTINGS_PATH, "r") as f:
            raw = json.load(f)

        def val(key, default):
            v = raw.get(key, default)
            return v["value"] if isinstance(v, dict) and "value" in v else v

        return {
            "tray_status": val("tray_status", 2),
            "startup": val("startup", 0),
            "alternate_hotkey": val("alternate_hotkey", "alt+ctrl+\\"),
        }
    except Exception:
        return {
            "tray_status": 2,
            "startup": 0,
            "alternate_hotkey": "alt+ctrl+\\",
        }


def save_settings(settings):
    try:
        try:
            with open(SETTINGS_PATH, "r") as f:
                raw = json.load(f)
        except Exception:
            raw = {}
        raw["tray_status"] = {
            "value": settings["tray_status"],
            "description": "0=Pause, 1=Tray Only, 2=Always On",
        }
        raw["startup"] = {
            "value": settings["startup"],
            "description": "0=Off, 1=On",
        }
        raw["alternate_hotkey"] = {
            "value": settings["alternate_hotkey"],
            "description": "Hotkey to trigger snip (e.g., 'ralt+rctrl+s')",
        }
        with open(SETTINGS_PATH, "w") as f:
            json.dump(raw, f, indent=4)
    except Exception as e:
        print("Failed to save settings:", e)


def create_autostart_entry():
    """Create a .desktop autostart entry for Snipping Lens."""
    try:
        os.makedirs(AUTOSTART_DIR, exist_ok=True)
        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            f'Exec=bash -c "{SETUP_SCRIPT}"\n'
            "Hidden=false\n"
            "NoDisplay=false\n"
            "X-GNOME-Autostart-enabled=true\n"
            "Name=Snipping Lens\n"
        )
        with open(DESKTOP_FILE, "w") as f:
            f.write(content)
        logging.info("Snipping Lens added to autostart.")
    except Exception as e:
        logging.error(f"Error adding Snipping Lens to autostart: {e}")


def remove_autostart_entry():
    """Remove the .desktop autostart entry for Snipping Lens."""
    try:
        if os.path.exists(DESKTOP_FILE):
            os.remove(DESKTOP_FILE)
            logging.info("Snipping Lens removed from autostart.")
    except Exception as e:
        logging.error(f"Error removing Snipping Lens from autostart: {e}")


def main(page: ft.Page):
    settings = load_settings()
    page.title = "Snipping Lens"
    page.window.width = 700
    page.window.height = 550
    page.window.min_width = 700
    page.window.min_height = 550
    page.window.center()
    page.horizontal_alignment = "center"
    page.vertical_alignment = "center"

    status_color_map = {
        0: "#ea4335",
        1: "#fbbc04",
        2: "#4285f4",
    }

    startup_color_map = {
        0: "#ea4335",
        1: "#4285f4",
    }

    def on_status_toggle(e):
        idx = int(e.data)
        settings["tray_status"] = idx
        save_settings(settings)
        status_toggle.selected_index = idx
        status_toggle.thumb_color = status_color_map[idx]
        page.update()

    status_toggle = ft.CupertinoSlidingSegmentedButton(
        selected_index=settings["tray_status"],
        thumb_color=status_color_map[settings["tray_status"]],
        on_change=on_status_toggle,
        padding=ft.padding.symmetric(0, 10),
        controls=[
            ft.Text("Pause", tooltip="Disable all features."),
            ft.Text(
                "Tray Only",
                tooltip="Trigger Google Lens searches only if snip is launched from the tray.",
            ),
            ft.Text(
                "Always On",
                tooltip="Trigger Google Lens searches regardless of where snip is launched from.",
            ),
        ],
    )

    def on_startup_toggle(e):
        idx = int(e.data)
        settings["startup"] = idx
        save_settings(settings)
        startup_toggle.selected_index = idx
        startup_toggle.thumb_color = startup_color_map[idx]

        if idx == 1:
            create_autostart_entry()
        else:
            remove_autostart_entry()

        page.update()

    startup_toggle = ft.CupertinoSlidingSegmentedButton(
        selected_index=settings["startup"],
        thumb_color=startup_color_map[settings["startup"]],
        on_change=on_startup_toggle,
        padding=ft.padding.symmetric(0, 10),
        controls=[
            ft.Text("Off"),
            ft.Text("On"),
        ],
    )

    # State for hotkey capture
    is_capturing_hotkey = [False]
    captured_keys = []

    def format_hotkey_display(keys):
        if not keys:
            return ""

        # Separate modifiers and regular keys, preserving left/right distinction
        modifiers = []
        regular_keys = []

        modifier_names = {
            "lctrl", "rctrl", "lalt", "ralt", "lshift", "rshift",
            "lwin", "rwin", "ctrl", "alt", "shift", "win",
        }

        for key in keys:
            if key.lower() in modifier_names:
                modifiers.append(key.lower())
            else:
                regular_keys.append(key.lower())

        modifiers = sorted(list(set(modifiers)))
        regular_keys = sorted(list(set(regular_keys)))

        all_keys = modifiers + regular_keys
        return "+".join(all_keys)

    def save_captured_hotkey():
        hotkey_str = format_hotkey_display(captured_keys)
        settings["alternate_hotkey"] = hotkey_str
        save_settings(settings)
        hotkey_field.value = hotkey_str if hotkey_str else ""
        hotkey_field.helper_text = "Click to capture new hotkey."
        is_capturing_hotkey[0] = False
        captured_keys.clear()
        page.update()
        logging.info(f"Hotkey updated to: '{hotkey_str}'")

    def on_hotkey_field_click(e):
        if not is_capturing_hotkey[0]:
            is_capturing_hotkey[0] = True
            captured_keys.clear()
            hotkey_field.value = "Recording keys..."
            hotkey_field.helper_text = "Press ENTER to save, and ESC to cancel."
            page.update()

    def on_key_down(e):
        try:
            if not is_capturing_hotkey[0]:
                return

            if e.key == "Escape":
                settings["alternate_hotkey"] = ""
                save_settings(settings)
                hotkey_field.value = ""
                hotkey_field.helper_text = "Hotkey cleared. Click to capture new hotkey."
                is_capturing_hotkey[0] = False
                captured_keys.clear()
                page.update()
                logging.info("Hotkey cleared.")
                return

            if e.key == "Enter":
                save_captured_hotkey()
                return

            current_keys = []

            # Check modifier states with left/right distinction
            # Flet's on_keyboard_event gives us e.ctrl, e.alt, e.shift, e.meta
            # but unfortunately doesn't natively distinguish left/right in the
            # boolean properties. We use e.key to detect the specific modifier.

            # Build the key name for left/right detection
            key_name = str(e.key).lower() if hasattr(e, "key") and e.key else ""

            # Check if the pressed key itself is a modifier with left/right info
            # Flet reports keys like "Control Left", "Alt Right", etc.
            combined = key_name
            if combined in MODIFIER_KEYS:
                current_keys.append(MODIFIER_KEYS[combined])
            elif key_name in GENERIC_MODIFIER_NAMES:
                # Generic modifier without side info
                pass
            else:
                # It's a regular key; add active modifiers
                try:
                    if hasattr(e, "ctrl") and e.ctrl:
                        # If we already have a specific l/r ctrl from a previous capture, keep it
                        if not any(k in captured_keys for k in ["lctrl", "rctrl"]):
                            current_keys.append("ctrl")
                except Exception:
                    pass

                try:
                    if hasattr(e, "alt") and e.alt:
                        if not any(k in captured_keys for k in ["lalt", "ralt"]):
                            current_keys.append("alt")
                except Exception:
                    pass

                try:
                    if hasattr(e, "shift") and e.shift:
                        if not any(k in captured_keys for k in ["lshift", "rshift"]):
                            current_keys.append("shift")
                except Exception:
                    pass

                try:
                    if hasattr(e, "meta") and e.meta:
                        if not any(k in captured_keys for k in ["lwin", "rwin"]):
                            current_keys.append("win")
                except Exception:
                    pass

                # Add the regular key
                key_mapping = {
                    "arrowup": "up",
                    "arrowdown": "down",
                    "arrowleft": "left",
                    "arrowright": "right",
                    " ": "space",
                    "delete": "del",
                }
                mapped_key = key_mapping.get(key_name, key_name)
                if mapped_key:
                    current_keys.append(mapped_key)

            # Accumulate modifier keys across presses, but replace regular keys
            if current_keys:
                modifier_set = {
                    "lctrl", "rctrl", "lalt", "ralt", "lshift", "rshift",
                    "lwin", "rwin", "ctrl", "alt", "shift", "win",
                }
                new_mods = [k for k in current_keys if k in modifier_set]
                new_regulars = [k for k in current_keys if k not in modifier_set]

                # Keep previously captured modifiers, add new ones
                existing_mods = [k for k in captured_keys if k in modifier_set]
                for m in new_mods:
                    if m not in existing_mods:
                        existing_mods.append(m)

                captured_keys.clear()
                captured_keys.extend(existing_mods)
                captured_keys.extend(new_regulars)

            if captured_keys:
                current_display = format_hotkey_display(captured_keys)
                hotkey_field.value = current_display
            else:
                hotkey_field.value = "Recording keys..."
            page.update()

        except Exception as ex:
            logging.error(f"Error in hotkey capture: {ex}")
            hotkey_field.value = "Error capturing keys. Click to try again."
            hotkey_field.helper_text = "Click to capture new hotkey."
            is_capturing_hotkey[0] = False
            captured_keys.clear()
            page.update()

    hotkey_field = ft.TextField(
        hint_text="Click to capture hotkey",
        value=settings["alternate_hotkey"],
        read_only=True,
        on_click=on_hotkey_field_click,
        width=300,
        border=ft.InputBorder.OUTLINE,
        helper_text="Click to capture new hotkey.",
    )

    log_field = ft.TextField(
        label="Live Log",
        read_only=True,
        multiline=True,
        min_lines=1,
        max_lines=12,
        value="Loading...",
        expand=True,
        autofocus=False,
        border=ft.InputBorder.OUTLINE,
        text_style=ft.TextStyle(size=13, font_family="monospace"),
    )

    page.add(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "Activation Mode",
                                    size=22,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                status_toggle,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Column(
                            [
                                ft.Text("Startup", size=22, weight=ft.FontWeight.BOLD),
                                startup_toggle,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=50,
                ),
                ft.Container(height=20),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "Snip Hotkey",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                hotkey_field,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                log_field,
            ]
        )
    )

    async def poll_log():
        while True:
            try:
                if os.path.exists(LOG_FILE):
                    with open(LOG_FILE, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        log_field.value = (
                            "".join(lines[-10:]) if lines else "(Log empty.)"
                        )
                else:
                    log_field.value = "(No log file found.)"
            except Exception as e:
                log_field.value = f"(Error reading log: {e})"
            log_field.update()
            await asyncio.sleep(1)

    def on_window_event(e):
        if e.data == "close":
            remove_lock()

    page.on_window_event = on_window_event

    try:
        page.on_keyboard_event = on_key_down
    except Exception as e:
        logging.warning(f"Could not set keyboard event handler: {e}")
        hotkey_field.read_only = False
        hotkey_field.helper_text = (
            "Type hotkey manually (e.g., ralt+rctrl+s) or click to try capture mode."
        )

    page.run_task(poll_log)


write_pid_lock()
try:
    ft.app(target=main)
finally:
    remove_lock()
