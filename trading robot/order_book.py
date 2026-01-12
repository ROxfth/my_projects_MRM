import logging

# Настройка логирования
logger = logging.getLogger(__name__)


# Получение данных из стакана
def get_order_book(exchange, symbol):
    try:
        order_book = exchange.fetch_order_book(symbol, limit=100)
        bids = order_book['bids']
        asks = order_book['asks']
        return bids, asks
    except Exception as e:
        logger.error(f"Ошибка при получении стакана для {symbol}: {e}")
        return [], []


# Анализ объемов в стакане
def analyze_order_book(exchange, symbol, levels, volume_threshold):
    bids, asks = get_order_book(exchange, symbol)
    if not bids or not asks:
        return None, None

    bid_volumes = [volume for _, volume in bids]
    ask_volumes = [volume for _, volume in asks]
    avg_volume = (sum(bid_volumes) + sum(ask_volumes)) / (len(bid_volumes) + len(ask_volumes))

    significant_levels = []
    for level_name, price in levels.items():
        for bid_price, bid_volume in bids:
            if abs(bid_price - price) / price < 0.001:
                if bid_volume > avg_volume * volume_threshold:
                    significant_levels.append(('bid', bid_price, bid_volume))
        for ask_price, ask_volume in asks:
            if abs(ask_price - price) / price < 0.001:
                if ask_volume > avg_volume * volume_threshold:
                    significant_levels.append(('ask', ask_price, ask_volume))

    logger.info(f"Значимые уровни для {symbol}: {significant_levels}")
    return significant_levels, avg_volume
