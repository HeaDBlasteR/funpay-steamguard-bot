import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def setup_logger() -> None:
    LOG_DIR.mkdir(exist_ok=True)

    file_handler = RotatingFileHandler(
        LOG_DIR / LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            file_handler,
        ],
        force=True,
    )
