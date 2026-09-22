import logging
import os
import sys
import threading

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


def _log_unhandled_exception(kind, value, traceback):
    logging.critical("Unhandled exception", exc_info=(kind, value, traceback))


def _log_unhandled_thread_exception(args):
    logging.critical(
        "Unhandled exception in thread %s",
        args.thread.name if args.thread else "unknown",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
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
    # both processes run under pythonw on Windows, which has no stderr, so a
    # crash would otherwise leave nothing behind
    sys.excepthook = _log_unhandled_exception
    threading.excepthook = _log_unhandled_thread_exception
