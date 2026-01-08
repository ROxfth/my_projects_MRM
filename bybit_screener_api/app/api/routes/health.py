from fastapi import APIRouter


router = APIRouter(tags=['health'])


@router.get('/health')
async def health() -> dict[str, str]:
    """
    Проверка работоспособности сервиса (health check).

    Эндпоинт используется для мониторинга и оркестраторов,
    чтобы убедиться, что приложение запущено и отвечает на запросы.

    Возвращает:
        dict[str, str]: Словарь со статусом сервиса.
        Ключ status имеет значение "ok", если сервис доступен.
    """
    return {'status': 'ok'}
