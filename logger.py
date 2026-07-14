import logging
import os
from logging.handlers import RotatingFileHandler

# Removing old logs file if it exists.
try:
    os.remove("logs.txt")
except:
    pass

# Clean layout format: HH:MM:SS | LEVEL | Message
LOG_FORMAT = "%(asctime)s | %(levelname)-5s | %(message)s"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt="%H:%M:%S",
    handlers=[
        RotatingFileHandler("logs.txt", mode="w+", maxBytes=5000000, backupCount=10),
        logging.StreamHandler(),
    ],
)

# Keep the background library noise quiet
logging.getLogger("pyrogram").setLevel(logging.ERROR)

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)