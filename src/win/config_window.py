import flet as ft
import os
import sys
import json
import asyncio

EXE_DIR = os.path.dirname(
    os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
)
LOCKFILE = os.path.join(EXE_DIR, ".flet_config.lock")
SETTINGS_PATH = os.path.join(EXE_DIR, "settings.json")
LOG_FILE = os.path.join(EXE_DIR, "sniplens.log")


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
        }
    except Exception:
        return {
            "tray_status": 2,
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
        with open(SETTINGS_PATH, "w") as f:
            json.dump(raw, f, indent=4)
    except Exception as e:
        print("Failed to save settings:", e)


def main(page: ft.Page):
    settings = load_settings()
    page.title = "Snipping Lens"
    page.window.icon = os.path.join(EXE_DIR, "sniplens.ico")
    page.window.width = 700
    page.window.height = 500
    page.window.min_width = 700
    page.window.min_height = 500
    page.window.center()
    page.horizontal_alignment = "center"
    page.vertical_alignment = "center"

    color_map = {
        0: "#ea4335",
        1: "#fbbc04",
        2: "#4285f4",
    }

    def on_status_toggle(e):
        idx = int(e.data)
        settings["tray_status"] = idx
        save_settings(settings)
        status_toggle.selected_index = idx
        status_toggle.thumb_color = color_map[idx]
        page.update()

    status_toggle = ft.CupertinoSlidingSegmentedButton(
        selected_index=settings["tray_status"],
        thumb_color=color_map[settings["tray_status"]],
        on_change=on_status_toggle,
        padding=ft.padding.symmetric(0, 10),
        controls=[
            ft.Text("Pause"),
            ft.Text("Tray Only"),
            ft.Text("Always On"),
        ],
    )

    log_field = ft.TextField(
        label="Live Log",
        read_only=True,
        multiline=True,
        min_lines=1,
        max_lines=15,
        value="Loading...",
        expand=True,
        autofocus=False,
        border=ft.InputBorder.OUTLINE,
        text_style=ft.TextStyle(size=13, font_family="Consolas"),
    )

    page.add(
        ft.Text("Mode", size=22, weight=ft.FontWeight.BOLD),
        status_toggle,
        log_field,
    )

    async def poll_log():
        while True:
            try:
                if os.path.exists(LOG_FILE):
                    with open(LOG_FILE, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        log_field.value = "".join(lines[-10:]) if lines else "(Log empty.)"
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

    page.run_task(poll_log)


write_pid_lock()
try:
    ft.app(target=main)
finally:
    remove_lock()
