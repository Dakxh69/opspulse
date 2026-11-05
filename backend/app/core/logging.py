"""
OpsPulse Backend — Structured Logging Configuration

Configures Python's standard logging to emit JSON-structured log records
when in production. In debug mode, uses a human-readable format.

Why structured logging?
- Machine-parseable JSON logs work with log aggregators (Loki, ELK, etc.).
- Human-readable format in debug mode improves developer experience.
- Consistent field names across all log records.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_object: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge any `extra` fields passed to the logger call.
        for key, value in record.__dict__.items():
            if key not in {
                "args",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "id",
                "levelname",
                "levelno",
                "lineno",
                "message",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            }:
                log_object[key] = value

        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_object, default=str)


def configure_logging(debug: bool | None = None) -> None:
    """Configure application logging. Called once at application startup.

    Args:
        debug: Override debug mode. If None, reads from app settings.
    """
    # Avoid circular import — only import settings here if needed.
    if debug is None:
        try:
            from app.core.config import settings

            debug = settings.DEBUG
            log_level = settings.LOG_LEVEL.upper()
        except Exception:
            debug = False
            log_level = "INFO"
    else:
        log_level = "DEBUG" if debug else "INFO"

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove any existing handlers (avoid duplicate log lines on reload).
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if debug:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = JSONFormatter()

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
