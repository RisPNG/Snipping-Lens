import logging
import os

from sniplens import paths

# libraries that narrate their own progress at INFO; the config window shows
# the tail of this log to the user, so only their warnings belong in it
NOISY_LOGGERS = (
    "httpx",
    "httpcore",
    "flet",
    "flet_components",
    "flet_controls",
    "flet_desktop",
    "flet_object_patch",
    "flet_transport",
)


def setup_logging():
    os.makedirs(paths.LOGS_DIR, exist_ok=True)
    logging.basicConfig(
        filename=paths.LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
