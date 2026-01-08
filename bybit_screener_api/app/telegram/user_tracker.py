import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import aiosqlite


logger: logging.Logger = logging.getLogger(__name__)


class UserTracker:
    """
    Класс для отслеживания пользователей и сбора статистики.

    Отвечает за:
    - регистрацию новых пользователей,
    - хранение даты первого обращения,
    - формирование агрегированной статистики,
    - генерацию текстовых отчётов.
    """

    def __init__(self, db_path: str = 'data/users.sqlite3') -> None:
        """
        Инициализировать трекер пользователей.

        Параметры:
            db_path (str): Путь к файлу базы данных SQLite.
        """
        self.db_path = db_path

    async def init(self) -> None:
        """
        Инициализировать структуру базы данных.

        Создаёт таблицу ``users``, если она ещё не существует.
        Используется при первом запуске приложения.
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    (
                        'CREATE TABLE IF NOT EXISTS users ('
                        '  chat_id INTEGER PRIMARY KEY,'
                        '  first_seen_ts INTEGER NOT NULL'
                        ')'
                    ),
                )
                await db.commit()
            logger.info('UserTracker успешно инициализирован. SQLite DB: %s', self.db_path)
        except Exception:
            logger.exception('Ошибка при инициализации базы данных SQLite: %s', self.db_path)

    async def add_user(self, chat_id: int) -> None:
        """
        Зарегистрировать нового пользователя.

        Добавляет пользователя в базу данных, если он ещё
        не был зарегистрирован ранее.

        Параметры:
            chat_id (int): Идентификатор чата пользователя в Telegram.
        """
        moscow_tz = ZoneInfo('Europe/Moscow')
        first_seen_ts = int(datetime.now(moscow_tz).timestamp())

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR IGNORE INTO users(chat_id, first_seen_ts) VALUES(?, ?)',
                    (chat_id, first_seen_ts),
                )
                await db.commit()
            logger.info('UserTracker: пользователь зарегистрирован chat_id=%s', chat_id)
        except Exception:
            logger.exception('Не удалось зарегистрировать пользователя chat_id=%s', chat_id)

    async def get_user_stats(self) -> dict:
        """
        Получить статистику пользователей.

        Подсчитывает количество пользователей:
        - за последние 24 часа,
        - за последние 30 дней,
        - за всё время.

        Возвращает:
            dict[str, int]: Словарь со следующими ключами:
                - daily_users — новые пользователи за сутки,
                - monthly_users — новые пользователи за месяц,
                - total_users — общее количество пользователей.
        """
        moscow_tz = ZoneInfo('Europe/Moscow')
        now = datetime.now(moscow_tz)
        day_ago_ts = int((now - timedelta(days=1)).timestamp())
        month_ago_ts = int((now - timedelta(days=30)).timestamp())

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                async with db.execute('SELECT COUNT(*) AS cnt FROM users') as cur:
                    total_users = int((await cur.fetchone())['cnt'])

                async with db.execute(
                    'SELECT COUNT(*) AS cnt FROM users WHERE first_seen_ts >= ?',
                    (day_ago_ts,),
                ) as cur:
                    daily_users = int((await cur.fetchone())['cnt'])

                async with db.execute(
                    'SELECT COUNT(*) AS cnt FROM users WHERE first_seen_ts >= ?',
                    (month_ago_ts,),
                ) as cur:
                    monthly_users = int((await cur.fetchone())['cnt'])

            return {
                'daily_users': daily_users,
                'monthly_users': monthly_users,
                'total_users': total_users,
            }
        except Exception:
            logger.exception('Ошибка при получении статистики пользователей')
            return {
                'daily_users': 0,
                'monthly_users': 0,
                'total_users': 0,
            }

    async def generate_report(self) -> str:
        """
        Сформировать текстовый отчёт по пользователям.

        Используется для отправки статистики владельцу
        приложения через Telegram.

        Возвращает:
            str: Отформатированный HTML-текст отчёта.
        """
        stats = await self.get_user_stats()
        return (
            '<b>Отчёт о новых пользователях:</b>\n'
            f'📅 За последние 24 часа: {stats["daily_users"]} новых пользователей\n'
            f'📆 За последний месяц: {stats["monthly_users"]} новых пользователей\n'
            f'🌐 За всё время: {stats["total_users"]} пользователей'
        )
