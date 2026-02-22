import asyncio
import atexit
import logging
import os
import signal
import sys
from pathlib import Path

import flet as ft

from settings import (
    ICON_PATH,
    LOCKFILE_CONFIG,
    LOG_FILE,
    SETUP_LINUX_SH,
    load_settings,
    save_settings,
)


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def write_pid_lock() -> None:
    try:
        with open(LOCKFILE_CONFIG, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def remove_lock() -> None:
    try:
        if os.path.exists(LOCKFILE_CONFIG):
            os.remove(LOCKFILE_CONFIG)
    except Exception:
        pass


def signal_handler(signum, frame) -> None:
    logging.info("Config window received signal %s, exiting...", signum)
    remove_lock()
    sys.exit(0)


AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_DESKTOP = AUTOSTART_DIR / "snipping-lens-startup.desktop"


def set_startup(enabled: bool) -> None:
    if enabled:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        setup_path = os.path.abspath(SETUP_LINUX_SH)
        desktop = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Exec=bash -lc '\"{setup_path}\"'\n"
            "Terminal=false\n"
            "Hidden=false\n"
            "NoDisplay=false\n"
            "X-GNOME-Autostart-enabled=true\n"
            "Name=Start Snipping Lens\n"
        )
        AUTOSTART_DESKTOP.write_text(desktop, encoding="utf-8")
        logging.info("Autostart enabled: %s", AUTOSTART_DESKTOP)
    else:
        try:
            if AUTOSTART_DESKTOP.exists():
                AUTOSTART_DESKTOP.unlink()
                logging.info("Autostart disabled: %s", AUTOSTART_DESKTOP)
        except Exception:
            logging.info("Failed to remove autostart entry: %s", AUTOSTART_DESKTOP)


async def main(page: ft.Page):
    settings = load_settings()

    page.title = "Snipping Lens"
    page.window.icon = os.path.abspath(ICON_PATH)
    page.window.width = 700
    page.window.height = 550
    page.window.min_width = 700
    page.window.min_height = 550
    await page.window.center()
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
        selected_index=int(settings.get("tray_status", 2)),
        thumb_color=status_color_map[int(settings.get("tray_status", 2))],
        on_change=on_status_toggle,
        padding=ft.Padding.symmetric(vertical=0, horizontal=10),
        controls=[
            ft.Text("Pause", tooltip="Disable snipping and hotkeys."),
            ft.Text(
                "Tray Only",
                tooltip="Snip only from the tray/menu (hotkey disabled).",
            ),
            ft.Text(
                "Always On",
                tooltip="Snip from tray/menu or the global hotkey.",
            ),
        ],
    )

    def on_startup_toggle(e):
        idx = int(e.data)
        settings["startup"] = idx
        save_settings(settings)
        startup_toggle.selected_index = idx
        startup_toggle.thumb_color = startup_color_map[idx]

        set_startup(idx == 1)
        page.update()

    startup_toggle = ft.CupertinoSlidingSegmentedButton(
        selected_index=int(settings.get("startup", 0)),
        thumb_color=startup_color_map[int(settings.get("startup", 0))],
        on_change=on_startup_toggle,
        padding=ft.Padding.symmetric(vertical=0, horizontal=10),
        controls=[
            ft.Text("Off"),
            ft.Text("On"),
        ],
    )

    # State for hotkey capture
    is_capturing_hotkey = [False]
    captured_keys: list[str] = []

    def format_hotkey_display(keys: list[str]) -> str:
        if not keys:
            return ""

        modifiers = []
        regular_keys = []

        for key in keys:
            k = key.lower()
            if k in [
                "ctrl",
                "alt",
                "shift",
                "win",
                "cmd",
                "meta",
                "super",
                "rctrl",
                "ralt",
                "lctrl",
                "lalt",
            ]:
                modifiers.append(k)
            else:
                regular_keys.append(k)

        modifiers = sorted(list(set(modifiers)))
        regular_keys = sorted(list(set(regular_keys)))
        return "+".join(modifiers + regular_keys)

    def save_captured_hotkey() -> None:
        hotkey_str = format_hotkey_display(captured_keys)
        save_hotkey_value(hotkey_str)
        hotkey_field.value = hotkey_str if hotkey_str else ""
        hotkey_field.helper = "Click to capture new hotkey."
        is_capturing_hotkey[0] = False
        captured_keys.clear()
        page.update()
        logging.info("Hotkey updated to: '%s'", hotkey_str)

    def on_hotkey_field_click(e):
        if not is_capturing_hotkey[0]:
            is_capturing_hotkey[0] = True
            captured_keys.clear()
            hotkey_field.value = "Recording keys..."
            hotkey_field.helper = "Press ENTER to save, and ESC to clear."
            page.update()

    def save_hotkey_value(value: str) -> None:
        hotkey_str = str(value or "").strip()
        settings["alternate_hotkey"] = hotkey_str
        save_settings(settings)
        logging.info("Hotkey updated to: '%s'", hotkey_str)

    def on_key_down(e):
        try:
            if not is_capturing_hotkey[0]:
                return

            if e.key == "Escape":
                settings["alternate_hotkey"] = ""
                save_settings(settings)
                hotkey_field.value = ""
                hotkey_field.helper = "Hotkey cleared. Click to capture new hotkey."
                is_capturing_hotkey[0] = False
                captured_keys.clear()
                page.update()
                logging.info("Hotkey cleared.")
                return

            if e.key == "Enter":
                save_captured_hotkey()
                return

            current_keys: list[str] = []

            # Modifier states (Flet may not expose left/right consistently).
            try:
                if hasattr(e, "ctrl") and e.ctrl:
                    current_keys.append("ctrl")
            except Exception:
                pass
            try:
                if hasattr(e, "alt") and e.alt:
                    current_keys.append("alt")
            except Exception:
                pass
            try:
                if hasattr(e, "shift") and e.shift:
                    current_keys.append("shift")
            except Exception:
                pass
            try:
                if hasattr(e, "meta") and e.meta:
                    current_keys.append("super")
            except Exception:
                pass

            key_name = str(e.key).lower() if hasattr(e, "key") and e.key else ""
            if key_name and key_name not in ["control", "alt", "shift", "meta", "cmd"]:
                key_mapping = {
                    "arrowup": "up",
                    "arrowdown": "down",
                    "arrowleft": "left",
                    "arrowright": "right",
                    " ": "space",
                    "delete": "del",
                }
                current_keys.append(key_mapping.get(key_name, key_name))

            captured_keys.clear()
            captured_keys.extend(current_keys)

            hotkey_field.value = (
                format_hotkey_display(captured_keys) or "Recording keys..."
            )
            page.update()

        except Exception as ex:
            logging.error("Error in hotkey capture: %s", ex)
            hotkey_field.value = "Error capturing keys. Click to try again."
            hotkey_field.helper = "Click to capture new hotkey."
            is_capturing_hotkey[0] = False
            captured_keys.clear()
            page.update()

    hotkey_field = ft.TextField(
        hint_text="Click to capture hotkey",
        value=str(settings.get("alternate_hotkey", "")).strip(),
        read_only=True,
        on_click=on_hotkey_field_click,
        on_blur=lambda e: (
            None
            if is_capturing_hotkey[0]
            else save_hotkey_value(hotkey_field.value)
        ),
        on_submit=lambda e: (
            None
            if is_capturing_hotkey[0]
            else save_hotkey_value(hotkey_field.value)
        ),
        width=320,
        border=ft.InputBorder.OUTLINE,
        helper="Click to capture new hotkey.",
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
                ft.Container(height=20),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "Global Snip Hotkey (X11)",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                hotkey_field,
                                ft.Text(
                                    "Tip: You can type right-side modifiers as 'rctrl' and 'ralt' (e.g. rctrl+ralt+s).",
                                    size=12,
                                    color="#b0b0b0",
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        )
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
        logging.warning("Could not set keyboard event handler: %s", e)
        hotkey_field.read_only = False
        hotkey_field.helper = "Type hotkey manually (e.g., rctrl+ralt+s)."

    page.run_task(poll_log)


write_pid_lock()
atexit.register(remove_lock)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
try:
    ft.run(main, assets_dir=None)
finally:
    remove_lock()
