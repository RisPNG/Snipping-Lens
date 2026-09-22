import logging
import os

from sniplens import APP_NAME, paths

LNK_NAME = f"{APP_NAME}.lnk"

if paths.IS_WINDOWS:
    import winshell

    ROOT_LNK = os.path.join(paths.ROOT, LNK_NAME)
    LNK_ICON = os.path.join(paths.ASSETS_DIR, "sniplens.ico")
    # pythonw runs without a console, so the shortcut needs no script wrapper
    # to hide one for it
    PYTHONW = os.path.join(paths.VENV_DIR, "Scripts", "pythonw.exe")
    LNK_ARGUMENTS = f'"{paths.MAIN_SCRIPT}"'
else:
    AUTOSTART_FILE = os.path.expanduser(
        "~/.config/autostart/snipping-lens-startup.desktop"
    )
    APP_MENU_FILE = os.path.expanduser(
        "~/.local/share/applications/snipping-lens.desktop"
    )
    SETUP_SCRIPT = os.path.join(paths.ROOT, "setup_linux.sh")
    # quoted per the Desktop Entry spec so an install path containing spaces
    # still launches, and run through bash so the script needs no exec bit
    LAUNCH_COMMAND = f'bash "{SETUP_SCRIPT}" --hidden'

    AUTOSTART_CONTENT = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Exec={LAUNCH_COMMAND}\n"
        "Terminal=false\n"
        "Hidden=false\n"
        "NoDisplay=false\n"
        "X-GNOME-Autostart-enabled=true\n"
        f"Name={APP_NAME}\n"
    )
    APP_MENU_CONTENT = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Exec={LAUNCH_COMMAND}\n"
        "Terminal=false\n"
        f"Icon={paths.TRAY_ICON_PATH}\n"
        f"Name={APP_NAME}\n"
        "Comment=Screenshot to Google Lens\n"
        "Categories=Utility;\n"
    )


def ensure_integration_entries(startup_enabled, app_menu_enabled=False):
    """Recreates this install's shortcuts so they keep pointing at the current
    folder after the user moves the project. Called on every app start."""
    if paths.IS_WINDOWS:
        _ensure_lnk(ROOT_LNK)
        if startup_enabled:
            _ensure_lnk(os.path.join(winshell.startup(), LNK_NAME))
    else:
        if startup_enabled:
            _write_desktop_file(AUTOSTART_FILE, AUTOSTART_CONTENT)
        if app_menu_enabled:
            _write_desktop_file(APP_MENU_FILE, APP_MENU_CONTENT)


def set_startup(enabled):
    if paths.IS_WINDOWS:
        startup_lnk = os.path.join(winshell.startup(), LNK_NAME)
        if enabled:
            _ensure_lnk(ROOT_LNK)
            _ensure_lnk(startup_lnk)
            logging.info("%s added to startup.", APP_NAME)
        else:
            _remove(startup_lnk)
            logging.info("%s removed from startup.", APP_NAME)
    else:
        if enabled:
            _write_desktop_file(AUTOSTART_FILE, AUTOSTART_CONTENT)
            logging.info("%s added to autostart.", APP_NAME)
        else:
            _remove(AUTOSTART_FILE)
            logging.info("%s removed from autostart.", APP_NAME)


def set_app_menu(enabled):
    if paths.IS_WINDOWS:
        return
    if enabled:
        _write_desktop_file(APP_MENU_FILE, APP_MENU_CONTENT)
        logging.info("%s added to the app menu.", APP_NAME)
    else:
        _remove(APP_MENU_FILE)
        logging.info("%s removed from the app menu.", APP_NAME)


if paths.IS_WINDOWS:

    def _ensure_lnk(lnk_path):
        if os.path.exists(lnk_path):
            link = winshell.shortcut(lnk_path)
            if (
                link.path
                and os.path.abspath(link.path) == os.path.abspath(PYTHONW)
                and link.arguments == LNK_ARGUMENTS
                and link.icon_location == (LNK_ICON, 0)
            ):
                return
        with winshell.shortcut(lnk_path) as link:
            link.path = PYTHONW
            link.arguments = LNK_ARGUMENTS
            link.icon_location = (LNK_ICON, 0)
            link.description = APP_NAME
            link.working_directory = paths.ROOT

else:

    def _write_desktop_file(path, content):
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    if f.read() == content:
                        return
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
        except OSError as e:
            logging.error("Failed to write %s: %s", path, e)


def _remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as e:
        logging.error("Failed to remove %s: %s", path, e)
