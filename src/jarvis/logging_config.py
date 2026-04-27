"""
jarvis.logging_config
=====================
Shared logging setup for all Jarvis services.

Usage:
    from jarvis.logging_config import configure_logging
    logger = configure_logging("agent", log_dir)
"""

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Noisy third-party loggers suppressed across all services
_SUPPRESS = ("httpx", "telegram", "apscheduler", "uvicorn.access")


def configure_logging(name: str, log_dir: Path) -> logging.Logger:
    """
    Configure file + stream logging for a named service.

    Creates a daily rotating log file at log_dir/<n>_YYYYMMDD.log.
    Both handlers log at DEBUG and above. launchd captures stdout automatically.

    Idempotent: returns the existing logger unchanged if already configured.
    Uses propagate=False so the root logger is never touched — safe to call
    from multiple modules or in test contexts without producing duplicate handlers.

    Args:
        name:    Service name used for logger name and log filename (e.g. "agent", "bot").
        log_dir: Directory for log files. Created if it does not exist.

    Returns:
        Configured logger instance for the named service.
    """
    log_dir = Path(log_dir).expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured — return as-is. Prevents duplicate handlers if
        # this function is called more than once in the same process.
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # manage our own handlers; don't bubble up to root

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"

    fh = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=3,              # keep .log, .log.1, .log.2, .log.3
        encoding="utf-8",
    )
    fh.setFormatter(fmt)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)

    for noisy in _SUPPRESS:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logger.info(f"Logging initialised | service={name} | log_file={log_file}")
    return logger
