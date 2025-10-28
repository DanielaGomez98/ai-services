import os
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

is_prod = os.getenv('IS_PROD', 'false').lower() == 'true'

logs_dir = Path("/tmp/logs")
# logs_dir = Path(__file__).parent.parent.parent.parent / "data" / "logs"

logs_dir.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("mining-microservice")
logger.setLevel(logging.DEBUG)

log_format = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)

file_handler = RotatingFileHandler(
    logs_dir / "app.log", maxBytes=5 * 1024 * 1024, backupCount=5
)
file_handler.setFormatter(log_format)
logger.addHandler(file_handler)


def get_logger():
    return logger
