"""
AI Call Analytics — Logging Configuration.

Configures structured logging for the backend application.
"""

import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Configure and return the application logger.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Configured root logger for the application.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logger = logging.getLogger("ai_call_analytics")
    logger.setLevel(log_level)

    # Avoid duplicate handlers on reload
    if not logger.handlers:
        logger.addHandler(handler)

    return logger
