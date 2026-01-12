import time
import logging
from config import DEPOSIT_USD, POSITION_PERCENT
from order_book import get_order_book

# Настройка логирования
logger = logging.getLogger(__name__)


# Проверка текущей цены относительно уровней
def check_price_proximity(exchange, symbol, levels):
    try:
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        for level_name, price in levels.items():
            if abs(current_price - price) / price < 0.002:
                logger.info(f"Цена {current_price} близка к уровню {level_name} для {symbol}: {price}")
                return level_name, price, current_price
        return None, None, current_price
    except Exception as e:
        logger.error(f"Ошибка при получении текущей цены для {symbol}: {e}")
        return None, None, None


# Получение текущего баланса
def get_balance(exchange):
    try:
        balance = exchange.fetch_balance()
        usdt_balance = balance['total'].get('USDT', 0)
        logger.info(f"Текущий баланс USDT: {usdt_balance}")
        return usdt_balance
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {e}")
        return 0


# Проверка открытых позиций
def has_open_position(exchange):
    try:
        positions = exchange.fetch_positions()
        for position in positions:
            if position['contracts'] > 0:
                logger.info(f"Открытая позиция: {position['symbol']}, {position['contracts']} контрактов")
                return True
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке позиций: {e}")
        return False


# Размещение ордера
def place_order(exchange, symbol, side, tp_percent, sl_percent, price=None, sl_price=None):
    try:
        current_price = exchange.fetch_ticker(symbol)['last']
        usdt_balance = get_balance(exchange)
        position_usdt = min(DEPOSIT_USD, usdt_balance) * (POSITION_PERCENT / 100)
        quantity = (position_usdt * exchange.markets[symbol]['contractSize'] / current_price)

        tp_price = current_price * (1 + tp_percent / 100) if side == 'buy' else current_price * (1 - tp_percent / 100)
        sl_price = sl_price if sl_price else current_price * (
                    1 - sl_percent / 100) if side == 'buy' else current_price * (1 + sl_percent / 100)

        order_type = 'market' if price is None else 'limit'
        params = {'takeProfit': str(tp_price), 'stopLoss': str(sl_price)}

        order = exchange.create_order(symbol, order_type, side, quantity, price, params)
        logger.info(f"Размещен ордер: {symbol}, {side}, {quantity}, {order_type}, TP: {tp_price}, SL: {sl_price}")
        return order
    except Exception as e:
        logger.error(f"Ошибка при размещении ордера для {symbol}: {e}")
        return None


# Мониторинг объема и закрытие позиции
def monitor_volume_and_close(exchange, symbol, order, significant_level, avg_volume, check_interval):
    initial_volume = significant_level[2]
    side = order['side']
    while True:
        bids, asks = get_order_book(exchange, symbol)
        current_volume = None
        for price, volume in (bids if significant_level[0] == 'bid' else asks):
            if abs(price - significant_level[1]) / significant_level[1] < 0.001:
                current_volume = volume
                break

        if current_volume is None or current_volume <= initial_volume * 0.5:
            logger.info(f"Объем уменьшился на 50% или снят для {symbol}. Закрытие позиции.")
            close_side = 'sell' if side == 'buy' else 'buy'
            place_order(exchange, symbol, close_side, 0, 0)
            return True
        time.sleep(check_interval)
