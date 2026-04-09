import logging
import sys

def get_logger(name: str) -> logging.Logger:
    """KidOS Core Kernel Logging Subsystem."""
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        # Advanced OS format styling (using standard ASCII formatting for logs)
        formatter = logging.Formatter(
            '%(asctime)s [KidOS] [%(levelname)s] %(name)s > %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
