"""Structured logging configuration with JSON formatter."""

import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Union


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs log records as JSON objects with timestamp, level, message, and context.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging(log_level: Union[str, Any] = "INFO") -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) as string or LogLevel enum
    """
    # Convert enum to string if needed
    level_str = str(log_level.value) if hasattr(log_level, "value") else str(log_level)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level_str.upper())

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level_str.upper())
    console_handler.setFormatter(JSONFormatter())

    # Add handler to root logger
    root_logger.addHandler(console_handler)

    # Set log levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
