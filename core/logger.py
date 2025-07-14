import logging
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'mr_cashondo_bot.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
