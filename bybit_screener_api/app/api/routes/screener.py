import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import CalculateRequest, CalculateResponse
from app.services.screener import ScreenerApp


router = APIRouter(prefix='/screener', tags=['screener'])


def get_screener_app() -> ScreenerApp:
    """
    Получить экземпляр приложения скринера.

    Возвращает:
        ScreenerApp: Экземпляр приложения скринера.
    """
    # Импорт выполняется лениво для предотвращения циклических импортов
    from app.main import screener_app

    return screener_app


@router.post('/calculate', response_model=CalculateResponse)
async def calculate(
        payload: CalculateRequest,
        app: ScreenerApp = Depends(get_screener_app),
) -> CalculateResponse:
    """
    Выполнить расчёт объёмов торгов в синхронном режиме.

    Эндпоинт запускает расчёт и ожидает полного завершения
    всех операций, включая отправку уведомлений (например, в Telegram),
    прежде чем вернуть HTTP-ответ.

    Параметры:
        payload (CalculateRequest): Входные данные расчёта, включая:
            - режим сканирования,
            - коэффициент порога,
            - идентификатор чата.
        app (ScreenerApp): Экземпляр приложения скринера,
            внедряемый через механизм зависимостей FastAPI.

    Исключения:
        HTTPException: Возникает при передаче неизвестного режима расчёта
        (код ответа 422).

    Возвращает:
        CalculateResponse: Результат выполнения операции со статусом ``"ok"``.
        """
    allowed_modes = {'top_10_pairs', 'top_50_pairs', 'top_100_pairs', 'all_pairs'}
    if payload.mode not in allowed_modes:
        raise HTTPException(status_code=422, detail=f'Unknown mode: {payload.mode}')

    # Выполняем расчёт асинхронно и ожидаем его завершения
    await app.calculate_large_volumes(payload.mode, payload.threshold_factor, payload.chat_id)
    return CalculateResponse(status='ok')


@router.post('/calculate/background', response_model=CalculateResponse)
async def calculate_background(
        payload: CalculateRequest,
        app: ScreenerApp = Depends(get_screener_app),
) -> CalculateResponse:
    """
    Запланировать расчёт объёмов торгов в фоновом режиме.

    Эндпоинт запускает расчёт в фоне с помощью asyncio.create_task
    и не ожидает его завершения. HTTP-ответ возвращается сразу
    после постановки задачи в очередь выполнения.

    Параметры:
        payload (CalculateRequest): Входные данные расчёта, включая:
            - режим сканирования,
            - коэффициент порога,
            - идентификатор чата.
        app (ScreenerApp): Экземпляр приложения скринера,
            внедряемый через механизм зависимостей FastAPI.

    Исключения:
        HTTPException: Возникает при передаче неизвестного режима расчёта
        (код ответа 422).

    Возвращает:
        CalculateResponse: Результат постановки задачи со статусом
        "scheduled".
    """
    allowed_modes = {'top_10_pairs', 'top_50_pairs', 'top_100_pairs', 'all_pairs'}
    if payload.mode not in allowed_modes:
        raise HTTPException(status_code=422, detail=f'Unknown mode: {payload.mode}')

    asyncio.create_task(app.calculate_large_volumes(payload.mode, payload.threshold_factor, payload.chat_id))
    return CalculateResponse(status='scheduled')
