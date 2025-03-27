import logging
import os
from datetime import datetime
from typing import Optional

def setup_logger(name: str = "scraper", level: int = logging.INFO) -> logging.Logger:
    """Set up and return a logger with the specified name and level"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Check if the logger already has handlers to avoid duplicate handlers
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        # Format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
    
    return logger

def log_action(logger: logging.Logger, message: str) -> None:
    """Log a user action message"""
    logger.info(message) 