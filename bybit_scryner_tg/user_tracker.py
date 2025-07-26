"""Модуль для отслеживания новых пользователей и формирования отчётов."""

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger: logging.Logger = logging.getLogger(__name__)


class UserTracker:
    """Класс для отслеживания новых пользователей и формирования отчётов."""

    def __init__(self, file_path: str = 'users.json'):
        """Инициализация трекера пользователей."""
        self.file_path = file_path
        self.users = self._load_users()
        logger.info('UserTracker инициализирован')

    def _load_users(self) -> dict:
        """Загружает данные о пользователях из JSON-файла."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info('Файл users.json не найден, создаётся новый')
            return {}
        except Exception as e:
            logger.error(f'Ошибка при загрузке users.json: {str(e)}')
            return {}

    def _save_users(self) -> None:
        """Сохраняет данные о пользователях в JSON-файл."""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=4)
            logger.info('Данные пользователей сохранены')
        except Exception as e:
            logger.error(f'Ошибка при сохранении users.json: {str(e)}')

    def add_user(self, chat_id: int) -> None:
        """Добавляет нового пользователя, если он ещё не зарегистрирован."""
        if str(chat_id) not in self.users:
            moscow_tz = ZoneInfo('Europe/Moscow')
            self.users[str(chat_id)] = {
                'first_seen': datetime.now(moscow_tz).isoformat()
            }
            self._save_users()
            logger.info(f'Добавлен новый пользователь: {chat_id}')

    def get_user_stats(self) -> dict:
        """Подсчитывает статистику пользователей за день, месяц и за всё время."""
        moscow_tz = ZoneInfo('Europe/Moscow')
        now = datetime.now(moscow_tz)
        day_ago = now - timedelta(days=1)
        month_ago = now - timedelta(days=30)  # Примерно месяц

        total_users = len(self.users)
        daily_users = 0
        monthly_users = 0

        for user_id, data in self.users.items():
            first_seen = datetime.fromisoformat(data['first_seen'])
            if first_seen >= day_ago:
                daily_users += 1
            if first_seen >= month_ago:
                monthly_users += 1

        return {
            'daily_users': daily_users,
            'monthly_users': monthly_users,
            'total_users': total_users
        }

    def generate_report(self) -> str:
        """Генерирует текстовый отчёт о статистике пользователей."""
        stats = self.get_user_stats()
        return (
            '<b>Отчёт о новых пользователях:</b>\n'
            f'📅 За последние 24 часа: {stats["daily_users"]} новых пользователей\n'
            f'📆 За последний месяц: {stats["monthly_users"]} новых пользователей\n'
            f'🌐 За всё время: {stats["total_users"]} пользователей'
        )