"""Central logging configuration.

Call `setup_logging()` once at process start. All app loggers use the "aes.*"
namespace so they can be filtered independently from framework logs.
"""
from __future__ import annotations

import logging
import sys

from app.core.config import settings

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Route uvicorn logs through the same handler/format.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = [handler]
        lg.propagate = False
        lg.setLevel(level)

    logging.getLogger("aes").setLevel(level)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return an app logger under the 'aes.' namespace."""
    return logging.getLogger(f"aes.{name}")
