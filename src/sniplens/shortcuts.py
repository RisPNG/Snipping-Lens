import logging
import os

from sniplens import paths

APP_NAME = "Snipping Lens"

if paths.IS_WINDOWS:
    import winshell

    ROOT_LNK = os.path.join(paths.ROOT, "Snipping Lens.lnk")
    RUN_VBS = os.path.join(paths.PLATFORM_DIR, "run.vbs")
    LNK_ICON = os.path.join(paths.ASSETS_DIR, "sniplens.ico")
else:
    AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
    APPLICATIONS_DIR = os.path.expanduser("~/.local/share/applications")
    AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "snipping-lens-startup.desktop")
    APP_MENU_FILE = os.path.join(APPLICATIONS_DIR, "snipping-lens.desktop")
    SETUP_SCRIPT = os.path.join(paths.ROOT, "setup_linux.sh")


def ensure_integration_entries(startup_enabled, app_menu_enabled=False):
    """Recreates this install's shortcuts so they keep pointing at the current
    folder after the user moves the project. Called on every app start."""
    if paths.IS_WINDOWS:
        _ensure_lnk(ROOT_LNK)
        if startup_enabled:
            _ensure_lnk(os.path.join(winshell.startup(), "Snipping Lens.lnk"))
    else:
        if startup_enabled:
            _write_desktop_file(AUTOSTART_FILE, _autostart_content())
        if app_menu_enabled:
            _write_desktop_file(APP_MENU_FILE, _app_menu_content())


def set_startup(enabled):
    if paths.IS_WINDOWS:
        startup_lnk = os.path.join(winshell.startup(), "Snipping Lens.lnk")
        if enabled:
            _ensure_lnk(ROOT_LNK)
            _ensure_lnk(startup_lnk)
            logging.info("Snipping Lens added to startup.")
        else:
            _remove(startup_lnk)
            logging.info("Snipping Lens removed from startup.")
    else:
        if enabled:
            _write_desktop_file(AUTOSTART_FILE, _autostart_content())
            logging.info("Snipping Lens added to autostart.")
        else:
            _remove(AUTOSTART_FILE)
            logging.info("Snipping Lens removed from autostart.")


def set_app_menu(enabled):
    if paths.IS_WINDOWS:
        return
    if enabled:
        _write_desktop_file(APP_MENU_FILE, _app_menu_content())
        logging.info("Snipping Lens added to the app menu.")
    else:
        _remove(APP_MENU_FILE)
        logging.info("Snipping Lens removed from the app menu.")


if paths.IS_WINDOWS:

    def _ensure_lnk(lnk_path):
        if os.path.exists(lnk_path):
            link = winshell.shortcut(lnk_path)
            if link.path and os.path.abspath(link.path) == os.path.abspath(RUN_VBS):
                return
        with winshell.shortcut(lnk_path) as link:
            link.path = RUN_VBS
            link.icon = (LNK_ICON, 0)
            link.description = APP_NAME
            link.working_directory = paths.ROOT

else:

    def _autostart_content():
        return (
            "[Desktop Entry]\n"
            "Type=Application\n"
            f'Exec=bash -c "{SETUP_SCRIPT} --hidden"\n'
            "Terminal=false\n"
            "Hidden=false\n"
            "NoDisplay=false\n"
            "X-GNOME-Autostart-enabled=true\n"
            f"Name={APP_NAME}\n"
        )

    def _app_menu_content():
        return (
            "[Desktop Entry]\n"
            "Type=Application\n"
            f'Exec=bash -c "{SETUP_SCRIPT} --hidden"\n'
            "Terminal=false\n"
            f"Icon={paths.TRAY_ICON_PATH}\n"
            f"Name={APP_NAME}\n"
            "Comment=Screenshot to Google Lens\n"
            "Categories=Utility;\n"
        )

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
