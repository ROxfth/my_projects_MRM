import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _to_bool(value: str | None, default: bool = False) -> bool:
    """
    Преобразовать строковое значение переменной окружения в логический тип.

    Поддерживаются распространённые «истинные» значения:
    '1', 'true', 'yes', 'y', 'on' (без учёта регистра).

    Параметры:
        value (str | None): Строковое значение переменной окружения.
        default (bool): Значение по умолчанию, используемое,
            если 'value' равно 'None'.

    Возвращает:
        bool: Результат преобразования в логический тип.
    """
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def _to_int(value: str | None) -> int | None:
    """
    Преобразовать строковое значение переменной окружения в целое число.

    Если значение отсутствует, пустое или не может быть
    преобразовано в int, возвращается None.

    Параметры:
        value (str | None): Строковое значение переменной окружения.

    Возвращает:
        int | None: Целое число или None при ошибке преобразования.
    """
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError:
        return None


@dataclass(frozen=True)
class Settings:
    """
    Настройки приложения, загружаемые из переменных окружения.

    Класс представляет собой неизменяемую (immutable) конфигурацию
    приложения. Значения читаются из переменных окружения при
    инициализации и используются во всех частях системы.
    """

    # API-ключ для доступа к внешнему сервису
    api_key: str | None = os.getenv("API_KEY")

    # Секретный ключ для доступа к внешнему сервису
    api_secret: str | None = os.getenv("API_SECRET")

    # Токен Telegram-бота
    tg_token: str | None = os.getenv("TG_TOKEN")

    # Идентификатор чата владельца бота в Telegram
    owner_chat_id: int | None = _to_int(os.getenv("OWNER_CHAT_ID"))

    # Флаг использования тестовой сети Bybit
    bybit_testnet: bool = _to_bool(os.getenv("BYBIT_TESTNET"), default=False)

    # Флаг запуска Telegram-бота при старте приложения
    run_telegram_bot: bool = _to_bool(os.getenv("RUN_TELEGRAM_BOT"), default=True)

    # Часовой пояс планировщика задач
    scheduler_timezone: str = os.getenv("SCHEDULER_TIMEZONE", "Europe/Moscow")

    # Час отправки ежедневного отчёта
    daily_report_hour: int = int(os.getenv("DAILY_REPORT_HOUR", "20"))

    # Минута отправки ежедневного отчёта.
    daily_report_minute: int = int(os.getenv("DAILY_REPORT_MINUTE", "0"))

    # Путь к базе данных пользователей
    user_db_path: str = os.getenv("USER_DB_PATH", "data/users.sqlite3")


settings = Settings()
