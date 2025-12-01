"""Minimal logging for Canvas LMS Automation

Usage:
    from core.log import log
    log.info("Starting...")
    log.error("Failed", exc_info=True)
"""
import logging
import sys
from typing import Optional

_logger: Optional[logging.Logger] = None


def _setup() -> logging.Logger:
    logger = logging.getLogger('canvas')
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter('[%(levelname).1s] %(message)s')

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = _setup()
    return _logger


# Shortcuts
log = get_logger()
debug = log.debug
info = log.info
warn = log.warning
error = log.error
