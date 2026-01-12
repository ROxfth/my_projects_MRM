import os
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

# Конфигурационные параметры
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
DEPOSIT_USD = float(os.getenv('DEPOSIT_USD', 100))
POSITION_PERCENT = float(os.getenv('POSITION_PERCENT', 10))
LEVERAGE = int(os.getenv('LEVERAGE', 10))
TAKE_PROFIT_PERCENT = float(os.getenv('TAKE_PROFIT_PERCENT', 0.5))
STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', 0.3))
VOLUME_THRESHOLD = int(os.getenv('VOLUME_THRESHOLD', 10))
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 60))
TESTNET = os.getenv('TESTNET', 'true').lower() == 'true'
