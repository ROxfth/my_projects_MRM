# Bybit Screener (FastAPI)

***Телеграмм бот*** определяющий крупные объемы в стакане заявок по фьючерсам 
криптомонет на бирже Bybit.

Проект построен на **FastAPI** выполняющий логику:
- расчёт плотностей (крупных объёмов) в ордербуке Bybit;
- Telegram-бот (aiogram) с меню и callback-логикой;
- ежедневный отчёт по пользователям через APScheduler.

## Структура

```
bybit_screener_api/
  app/
    main.py                 
    api/
      schemas.py
      routes/
        health.py
        screener.py
    core/
      settings.py
      logging.py
    services/
      bybit_client.py
      density_calculator.py
      screener.py           
    telegram/
      bot.py
      user_tracker.py
  data/
    users.sqlite3  
  docker-compose.yml
  Dockerfile         
  requirements.txt
  .env
```

## Переменные окружения

`.env`:

- `API_KEY`, `API_SECRET` — ключи Bybit
- `TG_TOKEN` — токен Telegram-бота
- `OWNER_CHAT_ID` — chat_id владельца для ежедневного отчёта
- `BYBIT_TESTNET` — `true/false` (по умолчанию false)
- `RUN_TELEGRAM_BOT` — `true/false` (по умолчанию true)
- `SCHEDULER_TIMEZONE` — по умолчанию `Europe/Moscow`
- `DAILY_REPORT_HOUR`, `DAILY_REPORT_MINUTE` — по умолчанию `20:00`
- `USER_DB_PATH` — путь к sqlite базе пользователей, по умолчанию `data/users.sqlite3`

## Запуск через Docker

1) Запуск:

```bash
docker compose up --build
```

2) Остановка:

```bash
docker compose down
```

SQLite база хранится в `./data`

## Эндпоинты

- `GET /health`
- `POST /screener/calculate` — выполнить расчёт и дождаться отправки результатов в Telegram
- `POST /screener/calculate/background` — запланировать расчёт в фоне и сразу вернуть ответ

Пример запроса:

```bash
curl -X POST 'http://localhost:8000/screener/calculate/background' \
  -H 'Content-Type: application/json' \
  -d '{"mode":"top_10_pairs","threshold_factor":8.0,"chat_id":123456789}'
```
