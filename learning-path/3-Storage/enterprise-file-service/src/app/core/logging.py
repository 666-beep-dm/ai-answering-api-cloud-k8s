import logging
import sys
from app.core.config import get_settings

_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    cfg = get_settings()
    level = logging.DEBUG if cfg.debug else logging.INFO
    logging.basicConfig(level=level, format=_FMT, datefmt=_DATE,
                        handlers=[logging.StreamHandler(sys.stdout)])
    for noisy in ("botocore", "boto3", "urllib3", "aiobotocore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
