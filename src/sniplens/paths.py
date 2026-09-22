import os

IS_WINDOWS = os.name == "nt"

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(SRC_DIR)
PLATFORM_DIR_NAME = "win" if IS_WINDOWS else "linux"
PLATFORM_DIR = os.path.join(ROOT, "bin", PLATFORM_DIR_NAME)
CONFIG_DIR = os.path.join(PLATFORM_DIR, "config")
LOGS_DIR = os.path.join(PLATFORM_DIR, "logs")
ASSETS_DIR = os.path.join(PLATFORM_DIR, "assets")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")
LOG_FILE = os.path.join(LOGS_DIR, "sniplens.log")
TRAY_ICON_PATH = os.path.join(ASSETS_DIR, "sniplens.png")
WINDOW_ICON_PATH = os.path.join(
    ASSETS_DIR, "sniplens.ico" if IS_WINDOWS else "sniplens.png"
)
CONFIG_WINDOW_SCRIPT = os.path.join(SRC_DIR, "config_window.py")
MAIN_SCRIPT = os.path.join(SRC_DIR, "main.py")
VENV_DIR = os.path.join(ROOT, "int", PLATFORM_DIR_NAME, "venv")
