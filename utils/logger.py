import logging
import sys
from logging.handlers import RotatingFileHandler
from config import LOGS_DIR

def setup_logger(name: str = "app", log_file: str = "app.log", level=logging.INFO):
    """Configures and returns a logger with rotating file handler and console handler."""
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File Handler (Rotating)
    file_handler = RotatingFileHandler(
        LOGS_DIR / log_file, 
        maxBytes=5*1024*1024, # 5 MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Create global application logger
app_logger = setup_logger("GestorVencimientos")


