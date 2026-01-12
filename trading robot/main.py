import logging
import time
from config import API_KEY, API_SECRET, LEVERAGE, TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, VOLUME_THRESHOLD, \
    CHECK_INTERVAL, TESTNET
from levels import init_exchange, set_leverage, find_support_resistance, get_top_liquid_symbols
from order_book import analyze_order_book, get_order_book
from trading import check_price_proximity, place_order, monitor_volume_and_close, has_open_position

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def trading_bot():
    # Инициализация биржи
    exchange = init_exchange(API_KEY, API_SECRET, TESTNET)

    # Получение топ-10 likвидных монет
    symbols = get_top_liquid_symbols(exchange)
    if not symbols:
        logger.error("Не удалось получить список ликвидных монет. Завершение.")
        return

    # Установка кредитного плеча для всех символов
    for symbol in symbols:
        set_leverage(exchange, symbol, LEVERAGE)

    while True:
        try:
            # Проверка открытых позиций
            if has_open_position(exchange):
                logger.info("Есть открытая позиция. Пропуск цикла.")
                time.sleep(CHECK_INTERVAL)
                continue

            for symbol in symbols:
                # Определяем уровни
                levels = find_support_resistance(exchange, symbol)
                level_name, level_price, current_price = check_price_proximity(exchange, symbol, levels)

                if level_name and level_price:
                    significant_levels, avg_volume = analyze_order_book(exchange, symbol, levels, VOLUME_THRESHOLD)
                    if significant_levels:
                        for level_type, sig_price, sig_volume in significant_levels:
                            if level_type == 'bid':
                                if current_price > level_price:  # Отбой от поддержки
                                    order = place_order(exchange, symbol, 'buy',
                                                        TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, sl_price=sig_price)
                                    if order:
                                        monitor_volume_and_close(exchange, symbol, order,
                                                                 (level_type, sig_price, sig_volume), avg_volume,
                                                                 CHECK_INTERVAL)
                                        break
                                elif current_price < level_price:  # Пробой поддержки
                                    if monitor_volume_and_close(exchange, symbol, {'side': 'buy', 'amount': 0},
                                                                (level_type, sig_price, sig_volume), avg_volume,
                                                                CHECK_INTERVAL):
                                        place_order(exchange, symbol, 'buy',
                                                    TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, sl_price=sig_price)
                                        break

                            elif level_type == 'ask':
                                if current_price < level_price:  # Отбой от сопротивления
                                    order = place_order(exchange, symbol, 'sell',
                                                        TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, sl_price=sig_price)
                                    if order:
                                        monitor_volume_and_close(exchange, symbol, order,
                                                                 (level_type, sig_price, sig_volume), avg_volume,
                                                                 CHECK_INTERVAL)
                                        break
                                elif current_price > level_price:  # Пробой сопротивления
                                    if monitor_volume_and_close(exchange, symbol, {'side': 'sell', 'amount': 0},
                                                                (level_type, sig_price, sig_volume), avg_volume,
                                                                CHECK_INTERVAL):
                                        place_order(exchange, symbol, 'sell',
                                                    TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, sl_price=sig_price)
                                        break
                if has_open_position(exchange):
                    break  # Выход из цикла по символам, если открыта позиция

            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"Ошибка в основном цикле: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    trading_bot()
