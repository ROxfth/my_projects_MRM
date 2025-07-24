import logging
from time import time
from collections import deque
import ccxt.async_support as ccxt

logger: logging.Logger = logging.getLogger(__name__)


class BybitClient:
    """Класс для работы с API Bybit."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True) -> None:
        """Инициализация клиента Bybit."""
        self.exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}  # Работа с фьючерсами
        })
        if testnet:
            self.exchange.set_sandbox_mode(True)
            logger.info('Используется тестовая сеть Bybit')
        else:
            logger.info('Используется реальная сеть Bybit')
        
        # Инициализация для ограничения запросов
        self.rate_limit = 1000  # Лимит запросов в минуту
        self.request_timestamps = deque()  # Очередь для хранения временных меток запросов

    def _check_rate_limit(self) -> bool:
        """Проверяет, не превышен ли лимит запросов."""
        current_time = time()
        # Удаляем метки времени старше 60 секунд
        while self.request_timestamps and current_time - self.request_timestamps[0] > 60:
            self.request_timestamps.popleft()
        
        # Проверяем количество запросов
        if len(self.request_timestamps) >= self.rate_limit:
            logger.warning('Достигнут лимит запросов: 500 запросов в минуту')
            return False
        
        self.request_timestamps.append(current_time)
        return True

    async def get_futures_pairs(self) -> list[str]:
        """Получает список всех фьючерсных пар с USDT."""
        if not self._check_rate_limit():
            return []
        
        try:
            await self.exchange.load_markets()
            pairs = [symbol for symbol in self.exchange.markets if symbol.endswith('/USDT:USDT')]
            logger.info(f'Получено {len(pairs)} фьючерсных пар')
            return pairs
        except Exception as e:
            logger.error(f'Ошибка при получении фьючерсных пар: {str(e)}')
            return []

    async def get_order_book(self, symbol: str, limit: int = 50) -> dict[str, list]:
        """Получает ордербук для указанной пары."""
        if not self._check_rate_limit():
            return {'bids': [], 'asks': []}
        
        try:
            order_book = await self.exchange.fetch_order_book(symbol, limit=limit)
            logger.info(
                f"Получена глубина ордербука для {symbol}: bids={len(order_book['bids'])}, asks={len(order_book['asks'])}")
            logger.debug(f"Пример bids: {order_book['bids'][:3] if order_book['bids'] else []}")
            logger.debug(f"Пример asks: {order_book['asks'][:3] if order_book['asks'] else []}")
            return order_book
        except Exception as e:
            logger.error(f'Ошибка при получении ордербука для {symbol}: {str(e)}')
            return {'bids': [], 'asks': []}

    async def close(self) -> None:
        """Закрывает соединение с биржей."""
        try:
            await self.exchange.close()
            logger.info('Соединение с Bybit закрыто')
        except Exception as e:
            logger.error(f'Ошибка при закрытии соединения: {str(e)}')
