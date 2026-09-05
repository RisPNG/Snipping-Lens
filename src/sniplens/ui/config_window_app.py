import asyncio
import logging
import os

import flet as ft

from sniplens import APP_NAME, paths
from sniplens.settings import SettingsStore
from sniplens.shortcuts import set_app_menu, set_startup

STATUS_COLORS = {
    0: "#ea4335",
    1: "#fbbc04",
    2: "#4285f4",
}

SWITCH_COLORS = {
    0: "#ea4335",
    1: "#4285f4",
}

# Modifier keys report a side on Linux ("Control Left") while the generic
# names arrive without one.
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

GENERIC_MODIFIERS = {"control": "ctrl", "alt": "alt", "shift": "shift", "meta": "win", "cmd": "win"}

MODIFIER_NAMES = {
    "lctrl", "rctrl", "lalt", "ralt", "lshift", "rshift", "lwin", "rwin",
    "ctrl", "alt", "shift", "win",
}

KEY_ALIASES = {
    "arrowup": "up",
    "arrowdown": "down",
    "arrowleft": "left",
    "arrowright": "right",
    " ": "space",
    "delete": "del",
}


def format_hotkey(keys):
    modifiers = sorted({k for k in keys if k in MODIFIER_NAMES})
    regulars = sorted({k for k in keys if k not in MODIFIER_NAMES})
    return "+".join(modifiers + regulars)


def build_config_window(page: ft.Page):
    store = SettingsStore()
    settings = store.load()

    page.title = APP_NAME
    page.window.icon = paths.WINDOW_ICON_PATH
    page.window.width = 700
    page.window.height = 550
    page.window.min_width = 700
    page.window.min_height = 550
    page.horizontal_alignment = ft.MainAxisAlignment.CENTER
    page.vertical_alignment = ft.CrossAxisAlignment.CENTER

    def save(updates):
        settings.update(updates)
        store.save(settings)

    def segmented(selected, options, colors, on_change):
        def handler(e):
            e.control.thumb_color = colors[e.control.selected_index]
            on_change(e.control.selected_index)

        return ft.CupertinoSlidingSegmentedButton(
            selected_index=selected,
            thumb_color=colors[selected],
            on_change=handler,
            padding=ft.Padding(10, 0, 10, 0),
            controls=[ft.Text(label, tooltip=tooltip) for label, tooltip in options],
        )

    status_toggle = segmented(
        settings["tray_status"],
        [
            ("Pause", "Disable all features."),
            ("Tray Only", "Trigger Google Lens searches only if snip is launched from the tray."),
            ("Always On", "Trigger Google Lens searches regardless of where the snip is launched from."),
        ],
        STATUS_COLORS,
        lambda index: save({"tray_status": index}),
    )

    def on_startup_change(index):
        save({"startup": index})
        set_startup(index == 1)

    startup_toggle = segmented(
        settings["startup"],
        [("Off", None), ("On", None)],
        SWITCH_COLORS,
        on_startup_change,
    )

    app_menu_toggle = None
    if not paths.IS_WINDOWS:

        def on_app_menu_change(index):
            save({"app_menu": index})
            set_app_menu(index == 1)

        app_menu_toggle = segmented(
            settings["app_menu"],
            [("Off", None), ("On", None)],
            SWITCH_COLORS,
            on_app_menu_change,
        )

    hotkey_bypass_toggle = segmented(
        int(settings["alternate_hotkey_bypass"]),
        [
            ("Off", None),
            ("On", "Allow the alternate hotkey to perform an image search in Tray Only mode."),
        ],
        SWITCH_COLORS,
        lambda index: save({"alternate_hotkey_bypass": bool(index)}),
    )

    is_capturing_hotkey = [False]
    captured_keys = []

    def refresh_hotkey_field():
        hotkey_field.value = settings["alternate_hotkey"] or (
            "Recording keys..." if is_capturing_hotkey[0] else ""
        )
        hotkey_field.helper = (
            "Press ENTER to save, and ESC to cancel."
            if is_capturing_hotkey[0]
            else "Click to capture new hotkey."
        )
        page.update()

    def on_hotkey_field_click(e):
        if not is_capturing_hotkey[0]:
            is_capturing_hotkey[0] = True
            captured_keys.clear()
            refresh_hotkey_field()

    def on_key_down(e: ft.KeyboardEvent):
        if not is_capturing_hotkey[0]:
            return
        if e.key == "Escape":
            is_capturing_hotkey[0] = False
            captured_keys.clear()
            save({"alternate_hotkey": ""})
            logging.info("Alternate hotkey cleared.")
            refresh_hotkey_field()
            return
        if e.key == "Enter":
            is_capturing_hotkey[0] = False
            save({"alternate_hotkey": format_hotkey(captured_keys)})
            captured_keys.clear()
            logging.info("Alternate hotkey updated to: '%s'", settings["alternate_hotkey"])
            refresh_hotkey_field()
            return

        key_name = (e.key or "").lower()
        if key_name in MODIFIER_KEYS:
            captured_keys[:] = [k for k in captured_keys if k not in ("ctrl", "alt", "shift", "win")]
            if MODIFIER_KEYS[key_name] not in captured_keys:
                captured_keys.append(MODIFIER_KEYS[key_name])
        elif key_name not in GENERIC_MODIFIERS:
            current = [k for k in captured_keys if k in MODIFIER_NAMES]
            if e.ctrl and "ctrl" not in current and not any(k in ("lctrl", "rctrl") for k in current):
                current.append("ctrl")
            if e.alt and "alt" not in current and not any(k in ("lalt", "ralt") for k in current):
                current.append("alt")
            if e.shift and "shift" not in current and not any(k in ("lshift", "rshift") for k in current):
                current.append("shift")
            if e.meta and "win" not in current and not any(k in ("lwin", "rwin") for k in current):
                current.append("win")
            current.append(KEY_ALIASES.get(key_name, key_name))
            captured_keys[:] = current
        hotkey_field.value = format_hotkey(captured_keys) or "Recording keys..."
        page.update()

    hotkey_field = ft.TextField(
        hint_text="Click to capture hotkey",
        value=settings["alternate_hotkey"],
        read_only=True,
        on_click=on_hotkey_field_click,
        width=300,
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
        text_style=ft.TextStyle(size=13, font_family="Consolas" if paths.IS_WINDOWS else "monospace"),
    )

    mode_columns = [
        ft.Column(
            [ft.Text("Activation Mode", size=22, weight=ft.FontWeight.BOLD), status_toggle],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        ft.Column(
            [ft.Text("Startup", size=22, weight=ft.FontWeight.BOLD), startup_toggle],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    ]
    if app_menu_toggle is not None:
        mode_columns.append(
            ft.Column(
                [ft.Text("App Menu", size=22, weight=ft.FontWeight.BOLD), app_menu_toggle],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    page.add(
        ft.Column(
            [
                ft.Row(
                    mode_columns,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=50,
                ),
                ft.Container(height=20),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "Snipping Tool Alt Hotkey"
                                    if paths.IS_WINDOWS
                                    else "Snip Hotkey",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                hotkey_field,
                                ft.Text(
                                    "Alt Hotkey Bypass",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                hotkey_bypass_toggle,
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
                if os.path.exists(paths.LOG_FILE):
                    with open(paths.LOG_FILE, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    log_field.value = "".join(lines[-10:]) if lines else "(Log empty.)"
                else:
                    log_field.value = "(No log file found.)"
            except Exception as e:
                log_field.value = f"(Error reading log: {e})"
            log_field.update()
            await asyncio.sleep(1)

    page.on_keyboard_event = on_key_down
    page.run_task(poll_log)


def run():
    if not paths.IS_WINDOWS:
        # the Flet client renders a black window on hybrid NVIDIA machines
        # unless GL is software-rendered; users can override by exporting it
        os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    ft.run(build_config_window)
