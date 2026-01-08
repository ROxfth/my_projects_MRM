from pydantic import BaseModel, Field


class CalculateRequest(BaseModel):
    """Модель входных данных для запуска расчёта скринера."""
    mode: str = Field(
        ...,
        description=(
            "Режим сканирования торговых пар. "
            "Допустимые значения: top_10_pairs, top_50_pairs, "
            "top_100_pairs, all_pairs."
        ),
    )
    threshold_factor: float = Field(
        8.0,
        ge=1.0,
        description=(
            "Множитель порогового значения для определения "
            "повышенной плотности объёмов торгов."
        ),
    )
    chat_id: int = Field(
        ...,
        description="Идентификатор чата Telegram, в который будут отправлены результаты.",
    )


class CalculateResponse(BaseModel):
    """
    Модель ответа API для операций расчёта.

    Содержит статус выполнения запроса или постановки задачи.
    """

    status: str = Field(
        ...,
        description=(
            "Статус выполнения операции. "
            "Возможные значения: ok, scheduled."
        ),
    )
