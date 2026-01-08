import asyncio
import logging
from collections.abc import Callable, Awaitable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.settings import settings
from app.services.bybit_client import BybitClient
from app.services.density_calculator import DensityCalculator
from app.telegram.bot import TelegramBot
from app.telegram.user_tracker import UserTracker


logger: logging.Logger = logging.getLogger(__name__)


CalculateCallback = Callable[[str, float, int], Awaitable[None]]
"""
Тип callback-функции для запуска расчёта плотностей.

Аргументы callback:
    - mode (str): режим сканирования,
    - threshold_factor (float): коэффициент порога,
    - chat_id (int): идентификатор Telegram-чата.
"""


class ScreenerApp:
    """
    Основная бизнес-логика приложения скринера.

    Класс объединяет:
    - клиента биржи Bybit,
    - вычисление плотностей объёмов,
    - Telegram-бота,
    - планировщик задач (APScheduler).

    Отвечает за обработку пользовательских запросов,
    периодические отчёты и отправку уведомлений.
    """

    def __init__(self) -> None:
        """
        Инициализировать приложение скринера.

        Настраивает клиента Bybit, Telegram-бота,
        трекер пользователей и планировщик задач.
        """
        if not settings.api_key or not settings.api_secret:
            logger.warning('API_KEY/API_SECRET не заданы. Запросы к Bybit могут завершаться ошибкой.')
        self.client = BybitClient(settings.api_key or '', settings.api_secret or '', testnet=settings.bybit_testnet)

        self.user_tracker = UserTracker(db_path=settings.user_db_path)

        if not settings.tg_token:
            logger.warning('TG_TOKEN не задан. Telegram-бот не будет запущен без токена.')

        self.bot = TelegramBot(settings.tg_token or '', self.user_tracker)
        self.density_calculator = DensityCalculator()

        # Последние отправленные плотности для фильтрации повторов
        self.last_densities: dict[str, dict] = {}

        self.bot.set_calculate_callback(self.calculate_large_volumes)

        self.scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.scheduler_timezone))
        self.scheduler.add_job(
            self.send_daily_report,
            trigger=CronTrigger(
                hour=settings.daily_report_hour,
                minute=settings.daily_report_minute,
                timezone=ZoneInfo(settings.scheduler_timezone),
            ),
            id='daily_user_report',
        )

    async def start_scheduler(self) -> None:
        """
        Запустить планировщик задач.

        Планировщик запускается только если он
        ещё не находится в состоянии выполнения.
        """
        if not self.scheduler.running:
            self.scheduler.start()

    async def shutdown(self) -> None:
        """
        Корректно завершить работу приложения.

        Останавливает планировщик и закрывает
        соединение с клиентом Bybit.
        """
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
        except Exception:
            logger.exception('Ошибка при остановке планировщика')

        await self.client.close()

    async def send_daily_report(self) -> None:
        """
        Отправить ежедневный отчёт владельцу приложения.

        Отчёт отправляется в Telegram-чат, указанный
        в настройках. Если chat_id не задан, отчёт пропускается.
        """
        if settings.owner_chat_id is None:
            logger.warning('OWNER_CHAT_ID не задан. Ежедневный отчёт не будет отправлен.')
            return
        await self.bot.send_report_to_owner(settings.owner_chat_id)

    async def calculate_large_volumes(self, mode: str, threshold_factor: float, chat_id: int) -> None:
        """
        Выполнить расчёт крупных объёмов и отправить результат в Telegram.

        В зависимости от режима выбирается набор торговых пар,
        затем для каждой пары анализируется стакан ордеров
        и вычисляются зоны повышенной плотности.

        Параметры:
            mode (str): Режим сканирования торговых пар.
            threshold_factor (float): Коэффициент порога
                для определения плотности.
            chat_id (int): Идентификатор Telegram-чата
                для отправки результатов.
        """
        try:
            logger.info('Запуск расчёта: mode=%s threshold_factor=%s chat_id=%s', mode, threshold_factor, chat_id)

            if mode in ['top_10_pairs', 'top_50_pairs', 'top_100_pairs']:
                try:
                    tickers = await self.client.exchange.fetch_tickers()
                    if not tickers:
                        await self._notify_rate_limited(chat_id)
                        return

                    limit = 10 if mode == 'top_10_pairs' else 50 if mode == 'top_50_pairs' else 100
                    symbols = sorted(
                        [
                            (symbol, ticker['baseVolume'])
                            for symbol, ticker in tickers.items()
                            if symbol.endswith('/USDT:USDT') and ticker.get('bid') and ticker.get('ask')
                        ],
                        key=lambda x: x[1],
                        reverse=True,
                    )[:limit]
                    symbols = [symbol for symbol, _ in symbols]
                except Exception:
                    logger.exception('Ошибка при получении тикеров')
                    await self.bot.send_large_volumes([], chat_id)
                    return
            else:
                symbols = await self.client.get_futures_pairs()
                if not symbols:
                    await self._notify_rate_limited(chat_id)
                    return
                symbols = symbols[:50]

            if not symbols:
                logger.error('Не получен список фьючерсных пар')
                await self.bot.send_large_volumes([], chat_id)
                return

            async def process_symbol(symbol: str) -> list[dict]:
                """
                Обработать одну торговую пару.

                Загружает стакан ордеров и вычисляет
                зоны плотности объёмов.
                """
                try:
                    order_book = await self.client.get_order_book(symbol)
                    if not order_book['bids'] and not order_book['asks']:
                        if len(self.client.request_timestamps) >= self.client.rate_limit:
                            await self._notify_rate_limited(chat_id)
                            return []
                        logger.warning('Пустой стакан ордеров для %s', symbol)
                        return []

                    return self.density_calculator.detect_large_volumes(order_book, symbol, threshold_factor)
                except Exception:
                    logger.exception('Ошибка при обработке символа %s', symbol)
                    return []

            results = await asyncio.gather(*[process_symbol(symbol) for symbol in symbols], return_exceptions=True)

            all_densities: list[dict] = []
            for density_list in results:
                if isinstance(density_list, list):
                    all_densities.extend(density_list)

            all_densities.sort(key=lambda x: x['volume_usdt'], reverse=True)

            new_densities = self._filter_new_densities(all_densities)

            if new_densities:
                if mode == 'top_10_pairs':
                    symbol_densities: dict[str, dict] = {}
                    for density in new_densities:
                        symbol = density['symbol']
                        if symbol not in symbol_densities or density['volume_usdt'] > symbol_densities[symbol]['volume_usdt']:
                            symbol_densities[symbol] = density
                    filtered_densities = list(symbol_densities.values())[:10]
                    await self.bot.send_large_volumes(filtered_densities, chat_id)
                else:
                    await self.bot.send_large_volumes(new_densities, chat_id)

                self.last_densities = {f"{d['symbol']}_{d['side']}_{d['price']}": d for d in all_densities}
            else:
                await self.bot.send_large_volumes([], chat_id)

        except Exception:
            logger.exception('Ошибка при расчёте крупных объёмов')
            await self.bot.send_large_volumes([], chat_id)

    def _filter_new_densities(self, density_list: list[dict]) -> list[dict]:
        """
        Отфильтровать новые или изменившиеся плотности объёмов.

        Сравнивает текущие данные с ранее отправленными,
        чтобы избежать повторной отправки одинаковых сигналов.

        Параметры:
            density_list (list[dict]): Список обнаруженных плотностей.

        Возвращает:
            list[dict]: Только новые или изменённые плотности.
                """
        new_densities: list[dict] = []
        for density in density_list:
            key = f"{density['symbol']}_{density['side']}_{density['price']}"
            if key not in self.last_densities or density['volume_usdt'] != self.last_densities[key]['volume_usdt']:
                new_densities.append(density)
        return new_densities

    async def _notify_rate_limited(self, chat_id: int) -> None:
        """
        Уведомить пользователя о превышении лимита запросов.

        Отправляет сообщение в Telegram с предложением
        повторить запрос позже.
        """
        await self.bot.send_message(
            chat_id,
            '<b>Количество запросов ограничено, через минуту можете повторить свой запрос.</b>',
            reply_markup=self.bot._get_menu_button(),
            parse_mode='HTML',
        )
