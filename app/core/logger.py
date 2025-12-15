"""
Centralized logging module for RNG-THING.
Provides colored console output and optional file logging with rotation.
"""

import logging
import sys
import json
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


# ANSI color codes for console output
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for console."""

    LEVEL_COLORS = {
        logging.DEBUG: Colors.GRAY,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.MAGENTA,
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)

        # Format the timestamp
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")

        # Build the formatted message
        level = f"{color}{record.levelname:<8}{Colors.RESET}"
        name = f"{Colors.CYAN}{record.name}{Colors.RESET}"
        message = record.getMessage()

        return f"{Colors.GRAY}{timestamp}{Colors.RESET} | {level} | {name} | {message}"


class PlainFormatter(logging.Formatter):
    """Plain formatter for file output (no colors)."""

    def format(self, record):
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        return f"{timestamp} | {record.levelname:<8} | {record.name} | {record.getMessage()}"


class JsonFormatter(logging.Formatter):
    """Formatter for structured logging in JSON format."""

    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%f%z"),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)

        # Add extra fields passed to the logger
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k not in logging.LogRecord.__dict__
        }
        if extra_fields:
            log_record.update(extra_fields)

        return json.dumps(log_record)


def setup_logger(
    name: str = "rng-thing",
    level: str = "INFO",
    log_to_file: bool = False,
    log_file_path: Optional[Path] = None,
    max_file_size: int = 5 * 1024 * 1024,  # 5MB
    backup_count: int = 3,
    formatter: str = "color",
) -> logging.Logger:
    """
    Set up and configure a logger.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to also log to a file
        log_file_path: Path for log file (defaults to data/app.log)
        max_file_size: Max size of log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Don't add handlers if already configured
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)

    if formatter == "json":
        console_handler.setFormatter(JsonFormatter())
    else:
        console_handler.setFormatter(ColoredFormatter())

    logger.addHandler(console_handler)

    # Optional file handler
    if log_to_file:
        try:
            if log_file_path is None:
                log_file_path = Path(__file__).parent.parent.parent / "data" / "app.log"

            log_file_path.parent.mkdir(exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file_path, maxBytes=max_file_size, backupCount=backup_count
            )
            file_handler.setFormatter(PlainFormatter())
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # Fallback to console only if file access fails
            sys.stderr.write(f"WARNING: Could not set up file logging: {e}\n")
            sys.stderr.write("Continuing with console logging only.\n")

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


# Default application logger
_app_logger: Optional[logging.Logger] = None


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance. If name is provided, returns a child logger.

    Args:
        name: Optional sub-logger name (e.g., "database", "api")

    Returns:
        Logger instance
    """
    global _app_logger

    if _app_logger is None:
        _app_logger = setup_logger()

    if name:
        return _app_logger.getChild(name)
    return _app_logger


def init_logging(
    level: str = "INFO", log_to_file: bool = False, formatter: str = "color"
):
    """
    Initialize the application logging system.
    Should be called once at application startup.

    Args:
        level: Log level
        log_to_file: Whether to enable file logging
    """
    global _app_logger
    _app_logger = setup_logger(
        level=level, log_to_file=log_to_file, formatter=formatter
    )
    _app_logger.info(f"Logging initialized at {level} level")
