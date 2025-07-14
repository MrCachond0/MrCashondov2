import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MT5_LOGIN = os.getenv('MT5_LOGIN')
    MT5_PASSWORD = os.getenv('MT5_PASSWORD')
    MT5_SERVER = os.getenv('MT5_SERVER')
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    RISK_MODE = os.getenv('RISK_MODE', 'fixed_usd')
    FIXED_RISK_USD = float(os.getenv('FIXED_RISK_USD', 1.0))
    # Agregar más parámetros según sea necesario
