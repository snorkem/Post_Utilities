"""Centralized logging configuration for the l3rds package.

This module provides a consistent logging interface across all modules,
with configurable levels, formats, and output destinations.
"""

import logging
import sys
from pathlib import Path
from typing import Final

# Default log format
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# Simple format for console output
CONSOLE_FORMAT: Final[str] = "%(levelname)s: %(message)s"

# Logger name prefix
LOGGER_PREFIX: Final[str] = "l3rds"

# Global flag to track if logging has been set up
_logging_configured = False


def setup_logging(
    level: int | str = logging.INFO,
    log_file: Path | str | None = None,
    console: bool = True,
    verbose: bool = False,
) -> None:
    """Configure logging for the application.

    This function should be called once at application startup to configure
    the root logger for all l3rds modules.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        console: Whether to log to console
        verbose: If True, use detailed format for console output

    Example:
        >>> setup_logging(level="DEBUG", log_file="generation.log")
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting generation")
    """
    global _logging_configured

    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper())

    # Get root logger for l3rds
    root_logger = logging.getLogger(LOGGER_PREFIX)
    root_logger.setLevel(level)

    # Clear existing handlers if re-configuring
    if _logging_configured:
        root_logger.handlers.clear()

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Use detailed format in verbose mode
        if verbose:
            console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
        else:
            console_formatter = logging.Formatter(CONSOLE_FORMAT)

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)

        # Create parent directory if needed
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Detailed debug information")
        >>> logger.info("Normal operation message")
        >>> logger.warning("Warning about potential issue")
        >>> logger.error("Error occurred but recoverable")
        >>> logger.critical("Critical error, cannot continue")
    """
    # Ensure logging is configured
    global _logging_configured
    if not _logging_configured:
        setup_logging()

    # Create logger under l3rds namespace
    if name.startswith(LOGGER_PREFIX):
        logger_name = name
    else:
        logger_name = f"{LOGGER_PREFIX}.{name}"

    return logging.getLogger(logger_name)


def set_level(level: int | str) -> None:
    """Change the logging level for all l3rds loggers.

    Args:
        level: New logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Example:
        >>> set_level("DEBUG")  # Enable debug logging
        >>> set_level(logging.WARNING)  # Only warnings and errors
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper())

    logger = logging.getLogger(LOGGER_PREFIX)
    logger.setLevel(level)

    # Update all handlers
    for handler in logger.handlers:
        handler.setLevel(level)


def disable_logging() -> None:
    """Disable all logging output.

    Useful for tests or when running in quiet mode.
    """
    logging.getLogger(LOGGER_PREFIX).setLevel(logging.CRITICAL + 1)


def enable_logging() -> None:
    """Re-enable logging after it was disabled."""
    logging.getLogger(LOGGER_PREFIX).setLevel(logging.INFO)
