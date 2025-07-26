import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from config import PUBLIC_KEY, SECRET_KEY, TELEGRAM_TOKEN, OWNER_CHAT_ID
from bybit_client import BybitClient
from density_calculator import DensityCalculator
from bot import TelegramBot
from user_tracker import UserTracker

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger: logging.Logger = logging.getLogger(__name__)


class Main:
    """Класс для управления логикой расчётов и взаимодействия с ботом."""

    def __init__(self):
        self.client = BybitClient(PUBLIC_KEY, SECRET_KEY, testnet=False)
        self.user_tracker = UserTracker()
        self.bot = TelegramBot(TELEGRAM_TOKEN, self.user_tracker)
        self.density_calculator = DensityCalculator()
        self.last_densities = {}  # Для хранения последних крупных объёмов
        self.bot.set_calculate_callback(self.calculate_large_volumes)
        self.scheduler = AsyncIOScheduler(timezone=ZoneInfo("Europe/Moscow"))
        self.scheduler.add_job(
            self.send_daily_report,
            trigger=CronTrigger(hour=20, minute=0, timezone=ZoneInfo("Europe/Moscow")),
            id="daily_user_report"
        )

    async def send_daily_report(self):
        """Отправляет ежедневный отчёт о пользователях владельцу."""
        await self.bot.send_report_to_owner(OWNER_CHAT_ID)

    async def calculate_large_volumes(self, mode: str, threshold_factor: float, chat_id: int) -> None:
        """Рассчитывает крупные объёмы по запросу."""
        try:
            logger.info(f"Начало расчёта для режима {mode} с множителем {threshold_factor} для чата {chat_id}")
            if mode in ["top_10_pairs", "top_50_pairs", "top_100_pairs"]:
                try:
                    tickers = await self.client.exchange.fetch_tickers()
                    if not tickers:  # Проверка на пустой результат из-за ограничения
                        await self.bot.send_message(
                            chat_id,
                            "<b>Количество запросов ограничено, через минуту можете повторить свой запрос.</b>",
                            reply_markup=self.bot._get_menu_button(),
                            parse_mode="HTML"
                        )
                        logger.info(f"Отправлено сообщение об ограничении запросов в чат {chat_id}")
                        return
                    logger.info(f"Получено {len(tickers)} тикеров")
                    limit = 10 if mode == "top_10_pairs" else 50 if mode == "top_50_pairs" else 100
                    symbols = sorted(
                        [(symbol, ticker['baseVolume']) for symbol, ticker in tickers.items()
                         if symbol.endswith('/USDT:USDT') and ticker.get('bid') and ticker.get('ask')],
                        key=lambda x: x[1], reverse=True
                    )[:limit]
                    symbols = [symbol for symbol, _ in symbols]
                    logger.info(f"Выбрано {len(symbols)} пар для обработки: {symbols}")
                except Exception as e:
                    logger.error(f"Ошибка при получении тикеров: {str(e)}")
                    await self.bot.send_large_volumes([], chat_id)
                    return
            else:
                symbols = await self.client.get_futures_pairs()
                if not symbols:  # Проверка на пустой результат из-за ограничения
                    await self.bot.send_message(
                        chat_id,
                        "<b>Количество запросов ограничено, через минуту можете повторить свой запрос.</b>",
                        reply_markup=self.bot._get_menu_button(),
                        parse_mode="HTML"
                    )
                    logger.info(f"Отправлено сообщение об ограничении запросов в чат {chat_id}")
                    return
                symbols = symbols[:50]  # Ограничение для всех пар
                logger.info(f"Получено {len(symbols)} фьючерсных пар: {symbols[:10]}...")

            if not symbols:
                logger.error("Не удалось получить фьючерсные пары")
                await self.bot.send_large_volumes([], chat_id)
                return

            async def process_symbol(symbol):
                try:
                    order_book = await self.client.get_order_book(symbol)
                    if not order_book['bids'] and not order_book['asks']:
                        if len(self.client.request_timestamps) >= self.client.rate_limit:
                            await self.bot.send_message(
                                chat_id,
                                "<b>Количество запросов ограничено, через минуту можете повторить свой запрос.</b>",
                                reply_markup=self.bot._get_menu_button(),
                                parse_mode="HTML"
                            )
                            logger.info(f"Отправлено сообщение об ограничении запросов в чат {chat_id}")
                            return []
                        logger.warning(f"Пустой ордербук для {symbol}")
                        return []
                    density_list = self.density_calculator.detect_large_volumes(
                        order_book, symbol, threshold_factor
                    )
                    logger.info(f"Для {symbol} найдено {len(density_list)} крупных объёмов")
                    return density_list
                except Exception as err:
                    logger.error(f"Ошибка при обработке пары {symbol}: {str(err)}")
                    return []

            tasks = [process_symbol(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            all_densities = []
            for density_list in results:
                if isinstance(density_list, list):
                    all_densities.extend(density_list)

            logger.info(f"Собрано {len(all_densities)} записей для отправки")
            for density in all_densities:
                logger.debug(f"Данные для отправки: {density}")

            # Сортировка по volume_usdt в порядке убывания
            all_densities.sort(key=lambda x: x['volume_usdt'], reverse=True)

            new_densities = self._filter_new_densities(all_densities)
            logger.info(f"После фильтрации {len(new_densities)} новых записей")

            if new_densities:
                if mode == "top_10_pairs":
                    # Ограничиваем до одной записи на символ (с наибольшим volume_usdt)
                    symbol_densities = {}
                    for density in new_densities:
                        symbol = density['symbol']
                        if symbol not in symbol_densities or density['volume_usdt'] > symbol_densities[symbol]['volume_usdt']:
                            symbol_densities[symbol] = density
                    filtered_densities = list(symbol_densities.values())[:10]
                    logger.info(f"Ограничено до {len(filtered_densities)} записей для топ-10 пар")
                    await self.bot.send_large_volumes(filtered_densities, chat_id)
                else:
                    await self.bot.send_large_volumes(new_densities, chat_id)
                self.last_densities = {
                    f"{d['symbol']}_{d['side']}_{d['price']}": d for d in all_densities
                }
            else:
                await self.bot.send_large_volumes([], chat_id)

        except Exception as e:
            logger.error(f"Ошибка в расчёте крупных объёмов: {str(e)}")
            await self.bot.send_large_volumes([], chat_id)

    def _filter_new_densities(self, density_list: list[dict]) -> list[dict]:
        """Фильтрует только новые или изменённые крупные объёмы."""
        new_densities = []
        for density in density_list:
            key = f"{density['symbol']}_{density['side']}_{density['price']}"
            if key not in self.last_densities or \
                    density['volume_usdt'] != self.last_densities[key]['volume_usdt']:
                new_densities.append(density)
        return new_densities

    async def start(self) -> None:
        """Запускает бота и планировщик."""
        self.scheduler.start()
        await self.bot.start()


async def main() -> None:
    """Основная функция для запуска бота."""
    main_app = Main()
    try:
        await main_app.start()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске: {str(e)}")
    finally:
        await main_app.client.close()


if __name__ == '__main__':
    asyncio.run(main())
