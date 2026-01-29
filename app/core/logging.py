# app/core/logging.py

import logging
import sys

def setup_logging():
    """Configure console logging for the application."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Change to DEBUG for more verbosity

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
