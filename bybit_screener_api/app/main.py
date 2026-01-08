import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import setup_logging
from app.core.settings import settings
from app.api.routes.health import router as health_router
from app.api.routes.screener import router as screener_router
from app.services.screener import ScreenerApp


logger: logging.Logger = logging.getLogger(__name__)

screener_app = ScreenerApp()

# фоновая задача tg бота
_telegram_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекст жизненного цикла FastAPI-приложения.

    Управляет инициализацией и корректным завершением
    фоновых сервисов:
    - настройка логирования,
    - инициализация базы пользователей,
    - запуск планировщика задач,
    - запуск Telegram-бота (при необходимости).

    Параметры:
        app (FastAPI): Экземпляр FastAPI-приложения.

    Yields:
        None: Управление передаётся приложению на время его работы.
    """
    global _telegram_task

    setup_logging()
    logger.info('Запуск приложения')

    await screener_app.user_tracker.init()

    await screener_app.start_scheduler()

    if settings.run_telegram_bot and settings.tg_token:
        _telegram_task = asyncio.create_task(screener_app.bot.start())
        logger.info('Запущен polling Telegram-бота')
    else:
        logger.info(
            'Polling Telegram-бота отключён (RUN_TELEGRAM_BOT=%s, TG_TOKEN=%s)',
            settings.run_telegram_bot,
            bool(settings.tg_token),
        )

    try:
        yield
    finally:
        logger.info('Завершение работы приложения')

        if _telegram_task is not None:
            _telegram_task.cancel()
            try:
                await _telegram_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception('Ошибка при остановке Telegram-бота')

        await screener_app.shutdown()


app = FastAPI(title='Bybit Screener API', version='1.0.0', lifespan=lifespan)

app.include_router(health_router)
app.include_router(screener_router)
