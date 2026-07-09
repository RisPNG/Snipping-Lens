import logging
import os

from sniplens import paths


def setup_logging():
    os.makedirs(paths.LOGS_DIR, exist_ok=True)
    logging.basicConfig(
        filename=paths.LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
