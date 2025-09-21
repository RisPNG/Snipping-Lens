import flet as ft
import os
import sys
import json
import asyncio
import winshell
import subprocess
import shutil
import logging

EXE_DIR = os.path.dirname(
    os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
)
LOCKFILE = os.path.join(EXE_DIR, ".flet_config.lock")
SETTINGS_PATH = os.path.abspath(os.path.join(EXE_DIR, "..", "config", "settings.json"))
LOG_FILE = os.path.abspath(os.path.join(EXE_DIR, "..", "logs", "sniplens.log"))
STARTUP = winshell.startup()
VBS_PATH = os.path.abspath(os.path.join(EXE_DIR, "..", "..", "..", "create_lnk.vbs"))
LNK_NAME = "Snipping Lens.lnk"
LNK_PATH = os.path.abspath(os.path.join(EXE_DIR, "..", "..", "..", LNK_NAME))

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

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
            "tray_status": val("tray_status", 0),
            "startup": val("startup", 0),
            "alternate_hotkey": val("alternate_hotkey", ""),
        }
    except Exception:
        return {
            "tray_status": 2,
            "startup": 0,
            "alternate_hotkey": "",
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
            "description": "Alternate hotkey for Windows Snipping Tool (e.g., 'ctrl+shift+s')",
        }
        with open(SETTINGS_PATH, "w") as f:
            json.dump(raw, f, indent=4)
    except Exception as e:
        print("Failed to save settings:", e)


def main(page: ft.Page):
    settings = load_settings()
    page.title = "Snipping Lens"
    page.window.icon = os.path.abspath(
        os.path.join(EXE_DIR, "..", "assets", "sniplens.ico")
    )
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

        startup_lnk_path = os.path.join(STARTUP, LNK_NAME)

        if idx == 1:
            try:
                subprocess.run(
                    ["cscript", VBS_PATH],
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if os.path.exists(LNK_PATH):
                    shutil.copy(LNK_PATH, startup_lnk_path)
                    logging.info("Snipping Lens added to startup.")
            except (subprocess.CalledProcessError, FileNotFoundError, OSError) as ex:
                logging.info("Error adding Snipping Lens to startup.")

        else:
            try:
                if os.path.exists(startup_lnk_path):
                    os.remove(startup_lnk_path)
                    logging.info("Snipping Lens removed from startup.")
            except OSError as ex:
                logging.info("Error removing Snipping Lens from startup.")

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
    is_capturing_hotkey = [False]  # Use list for mutable reference
    captured_keys = []

    def format_hotkey_display(keys):
        """Format captured keys for display"""
        if not keys:
            return ""

        # Sort modifiers first, then regular keys
        modifiers = []
        regular_keys = []

        for key in keys:
            if key.lower() in ["ctrl", "alt", "shift", "win", "cmd"]:
                modifiers.append(key.lower())
            else:
                regular_keys.append(key.lower())

        # Remove duplicates and sort
        modifiers = sorted(list(set(modifiers)))
        regular_keys = sorted(list(set(regular_keys)))

        all_keys = modifiers + regular_keys
        return "+".join(all_keys)

    def save_captured_hotkey():
        """Save the captured hotkey and stop capturing"""
        hotkey_str = format_hotkey_display(captured_keys)
        settings["alternate_hotkey"] = hotkey_str
        save_settings(settings)
        hotkey_field.value = hotkey_str if hotkey_str else ""
        hotkey_field.helper_text = (
            "Click to capture new hotkey."
        )
        is_capturing_hotkey[0] = False
        captured_keys.clear()
        page.update()
        logging.info(f"Alternate hotkey updated to: '{hotkey_str}'")

    def on_hotkey_field_click(e):
        """Start capturing hotkey when field is clicked"""
        if not is_capturing_hotkey[0]:
            is_capturing_hotkey[0] = True
            captured_keys.clear()
            hotkey_field.value = "Recording keys..."
            hotkey_field.helper_text = (
                "Press ENTER to save, and ESC to cancel."
            )
            page.update()

    def on_key_down(e):
        """Handle keyboard events for hotkey capture"""
        try:
            if not is_capturing_hotkey[0]:
                return

            # Handle ESC to clear hotkey
            if e.key == "Escape":
                settings["alternate_hotkey"] = ""
                save_settings(settings)
                hotkey_field.value = ""
                hotkey_field.helper_text = (
                    "Hotkey cleared. Click to capture new hotkey."
                )
                is_capturing_hotkey[0] = False
                captured_keys.clear()
                page.update()
                logging.info("Alternate hotkey cleared.")
                return

            # Handle Enter to save current captured keys
            if e.key == "Enter":
                save_captured_hotkey()
                return

            # Check for modifier keys using the event properties
            current_keys = []

            # Check modifier states - with error handling for missing properties
            try:
                if hasattr(e, "ctrl") and e.ctrl:
                    current_keys.append("ctrl")
            except:
                pass

            try:
                if hasattr(e, "alt") and e.alt:
                    current_keys.append("alt")
            except:
                pass

            try:
                if hasattr(e, "shift") and e.shift:
                    current_keys.append("shift")
            except:
                pass

            try:
                if hasattr(e, "meta") and e.meta:
                    current_keys.append("win")
            except:
                pass

            # Add the actual key if it's not a modifier
            key_name = str(e.key).lower() if hasattr(e, "key") and e.key else ""
            if key_name and key_name not in ["control", "alt", "shift", "meta", "cmd"]:
                # Handle special key names
                key_mapping = {
                    "arrowup": "up",
                    "arrowdown": "down",
                    "arrowleft": "left",
                    "arrowright": "right",
                    " ": "space",
                    "delete": "del",
                }
                mapped_key = key_mapping.get(key_name, key_name)
                current_keys.append(mapped_key)

            # Update captured keys with current combination
            captured_keys.clear()
            captured_keys.extend(current_keys)

            # Update display
            if captured_keys:
                current_display = format_hotkey_display(captured_keys)
                hotkey_field.value = (
                    f"{current_display}"
                )
            else:
                hotkey_field.value = "Recording keys..."
            page.update()

        except Exception as ex:
            # Fallback error handling - log error and stop capturing
            logging.error(f"Error in hotkey capture: {ex}")
            hotkey_field.value = "Error capturing keys. Click to try again."
            hotkey_field.helper_text = (
                "Click to capture new hotkey."
            )
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
        text_style=ft.TextStyle(size=13, font_family="Consolas"),
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
                ft.Container(height=20),  # Spacer
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "Snipping Tool Alt Hotkey",
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

    # Try to set keyboard event handler, but don't fail if it's not supported
    try:
        page.on_keyboard_event = on_key_down
    except Exception as e:
        logging.warning(f"Could not set keyboard event handler: {e}")
        # Fallback: Make the field editable if keyboard events don't work
        hotkey_field.read_only = False
        hotkey_field.helper_text = (
            "Type hotkey manually (e.g., ctrl+shift+s) or click to try capture mode."
        )

    page.run_task(poll_log)


write_pid_lock()
try:
    ft.app(target=main)
finally:
    remove_lock()
