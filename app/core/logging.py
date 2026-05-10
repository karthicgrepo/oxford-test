"""Logging configuration."""

from __future__ import annotations

import logging
import sys
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    """Configure root + uvicorn loggers with a consistent format."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "default",
                    "level": level,
                },
            },
            "loggers": {
                "": {"handlers": ["console"], "level": level},
                "uvicorn": {"handlers": ["console"], "level": level, "propagate": False},
                "uvicorn.error": {"handlers": ["console"], "level": level, "propagate": False},
                "uvicorn.access": {"handlers": ["console"], "level": level, "propagate": False},
                "httpx": {"handlers": ["console"], "level": "WARNING", "propagate": False},
            },
        }
    )
    logging.getLogger(__name__).debug("Logging configured at level=%s", level)
