import ccxt
import pandas as pd
import logging

# Настройка логирования
logger = logging.getLogger(__name__)


# Инициализация биржи
def init_exchange(api_key, api_secret, testnet):
    exchange = ccxt.bybit({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    })
    if testnet:
        exchange.set_sandbox_mode(True)
    return exchange


# Установка кредитного плеча
def set_leverage(exchange, symbol, leverage):
    try:
        exchange.set_leverage(leverage, symbol)
        logger.info(f"Установлено кредитное плечо {leverage}x для {symbol}")
    except Exception as e:
        logger.error(f"Ошибка при установке плеча: {e}")


# Получение исторических данных
def get_historical_data(exchange, symbol, timeframe, limit):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"Ошибка при получении исторических данных для {symbol}: {e}")
        return None


# Определение уровней поддержки и сопротивления
def find_support_resistance(exchange, symbol):
    levels = {}

    # Все время
    df_all = get_historical_data(exchange, symbol, '1d', 1000)
    if df_all is not None:
        levels['all_time_high'] = df_all['high'].max()
        levels['all_time_low'] = df_all['low'].min()

    # Месяц
    df_month = get_historical_data(exchange, symbol, '1d', 30)
    if df_month is not None:
        levels['month_high'] = df_month['high'].max()
        levels['month_low'] = df_month['low'].min()

    # Неделя
    df_week = get_historical_data(exchange, symbol, '4h', 42)
    if df_week is not None:
        levels['week_high'] = df_week['high'].max()
        levels['week_low'] = df_week['low'].min()

    # День
    df_day = get_historical_data(exchange, symbol, '1h', 24)
    if df_day is not None:
        levels['day_high'] = df_day['high'].max()
        levels['day_low'] = df_day['low'].min()

    logger.info(f"Уровни для {symbol}: {levels}")
    return levels


# Получение 10 самых ликвидных монет (кроме BTC)
def get_top_liquid_symbols(exchange, exclude_symbol='BTCUSDT', limit=10):
    try:
        markets = exchange.load_markets()
        tickers = exchange.fetch_tickers()
        symbols = []
        for symbol, ticker in tickers.items():
            if 'USDT' in symbol and symbol.endswith('USDT') and symbol != exclude_symbol:
                volume = ticker.get('quoteVolume', 0)
                symbols.append((symbol, volume))
        symbols.sort(key=lambda x: x[1], reverse=True)
        top_symbols = [s[0] for s in symbols[:limit]]
        logger.info(f"Топ {limit} ликвидных монет: {top_symbols}")
        return top_symbols
    except Exception as e:
        logger.error(f"Ошибка при получении ликвидных монет: {e}")
        return []
