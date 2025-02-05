"""Centralized logging configuration for the application."""

import logging
import sys
from typing import Optional
from pathlib import Path
from datetime import datetime

# Constants for log levels
LOG_LEVEL_PRODUCTION = logging.ERROR
LOG_LEVEL_DEBUG = logging.DEBUG

# Constants for log formats
DEBUG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
PROD_FORMAT = '%(message)s'

# Global debug flag
DEBUG = False


def setup_logger(
    debug: bool = False,
    log_file: Optional[str] = None,
    module_name: Optional[str] = None
) -> logging.Logger:
    """Configure and get a logger instance.

    Args:
        debug (bool): Whether to enable debug mode
        log_file (Optional[str]): Path to log file. If None, logs only to console
        module_name (Optional[str]): Name for the logger. If None, uses root logger

    Returns:
        logging.Logger: Configured logger instance
    """
    global DEBUG
    DEBUG = debug

    # Get or create logger
    logger = logging.getLogger(
        module_name) if module_name else logging.getLogger()

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Set base log level
    base_level = LOG_LEVEL_DEBUG if debug else LOG_LEVEL_PRODUCTION
    logger.setLevel(base_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter(DEBUG_FORMAT if debug else PROD_FORMAT)
    )
    logger.addHandler(console_handler)

    # File handler (if requested)
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(DEBUG_FORMAT))
        logger.addHandler(file_handler)

    # Configure specific loggers in production
    if not debug:
        # Silence verbose loggers
        for logger_name in [
            'whisper',
            'story_pipeline',
            'elevenlabs_api',
            'video_pipeline',
            'video_manager'
        ]:
            logging.getLogger(logger_name).setLevel(LOG_LEVEL_PRODUCTION)

    return logger


def get_logger(module_name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance. If not configured, sets up with default config.

    Args:
        module_name (Optional[str]): Name for the logger

    Returns:
        logging.Logger: Logger instance
    """
    logger = logging.getLogger(
        module_name) if module_name else logging.getLogger()

    # If logger not configured (no handlers), set up with defaults
    if not logger.handlers:
        logger = setup_logger(
            debug=DEBUG,
            module_name=module_name
        )

    return logger
