import os
from dotenv import load_dotenv

load_dotenv()

# API-ключи Bybit
PUBLIC_KEY: str = os.getenv('API_KEY')
SECRET_KEY: str = os.getenv('API_SECRET')

# API-ключи Bybit
TELEGRAM_TOKEN: str = os.getenv('TG_TOKEN')
# TELEGRAM_CHAT_ID удалён, так как теперь используется chat_id пользователя
OWNER_CHAT_ID: int = int(os.getenv('OWNER_CHAT_ID'))