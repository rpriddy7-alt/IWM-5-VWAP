"""
Structured logging setup for the IWM momentum system.
Provides timestamped, level-based logging to both console and file.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from config import Config


class CustomFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""
    
    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    format_str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    
    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: blue + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


def setup_logger(name: str = "IWM_Momentum") -> logging.Logger:
    """
    Set up logger with both console and file handlers.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler with color
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)
    
    # File handler with detailed format
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    file_handler = logging.FileHandler(
        log_dir / Config.LOG_FILE,
        mode='a',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger


def log_trade_event(logger: logging.Logger, event_type: str, data: dict):
    """
    Log a trade event with structured data.
    
    Args:
        logger: Logger instance
        event_type: Type of event (BUY, SELL, SIGNAL, etc.)
        data: Event data dictionary
    """
    timestamp = datetime.now().isoformat()
    log_entry = f"[{event_type}] {timestamp} | " + " | ".join(
        f"{k}={v}" for k, v in data.items()
    )
    logger.info(log_entry)


# Create default logger
default_logger = setup_logger()

