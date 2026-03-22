import logging
import sys
import os
from logging.handlers import RotatingFileHandler

os.makedirs("logs",exist_ok=True)
logger = logging.getLogger("AI_System")
logger.setLevel(logging.DEBUG)

log_format = logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_format)

file_handler = RotatingFileHandler(
    "logs/app.log", maxBytes=5*1024*1024, backupCount=3, encoding="utf-8"
)

file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_format)
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)