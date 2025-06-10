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
        # Create debug directory if it doesn't exist
        debug_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(os.path.join(debug_dir, f'{name}.log'))
        file_handler.setLevel(level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        # Format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Prevent propagation to root logger to avoid duplicate messages
        logger.propagate = False
    
    return logger

def log_action(logger: logging.Logger, message: str) -> None:
    """Log a user action message"""
    logger.info(message) 