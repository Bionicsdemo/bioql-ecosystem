#!/usr/bin/env python3
"""
BioQL Logging Module

Provides centralized logging functionality for the BioQL package.
"""

import logging
import sys
from typing import Optional
from pathlib import Path


class BioQLFormatter(logging.Formatter):
    """Custom formatter for BioQL log messages."""

    def __init__(self):
        super().__init__()
        self.datefmt = "%Y-%m-%d %H:%M:%S"

    def format(self, record):
        """Format log record with color coding for different levels."""
        # Color codes for different log levels
        colors = {
            'DEBUG': '\033[36m',     # Cyan
            'INFO': '\033[32m',      # Green
            'WARNING': '\033[33m',   # Yellow
            'ERROR': '\033[31m',     # Red
            'CRITICAL': '\033[35m'   # Magenta
        }
        reset = '\033[0m'

        # Add color if we're outputting to a terminal
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = colors.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{reset}"

        # Format the message
        formatter = logging.Formatter(
            '%(asctime)s - BioQL.%(name)s - %(levelname)s - %(message)s',
            datefmt=self.datefmt
        )
        return formatter.format(record)


def get_logger(name: str = "bioql") -> logging.Logger:
    """
    Get a configured logger for BioQL modules.

    Args:
        name: Name of the logger (usually module name)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(BioQLFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    quiet: bool = False
) -> None:
    """
    Configure logging for the entire BioQL package.

    Args:
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_file: Optional file to write logs to
        quiet: If True, suppress console output
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Add console handler unless quiet mode
    if not quiet:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(BioQLFormatter())
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)


def disable_logging():
    """Disable all logging output."""
    logging.disable(logging.CRITICAL)


def enable_logging():
    """Re-enable logging output."""
    logging.disable(logging.NOTSET)