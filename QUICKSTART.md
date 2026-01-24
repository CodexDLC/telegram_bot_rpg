# 🚀 Quick Start Guide

## Запуск сервисов

Проект разделён на **Backend API** (FastAPI) и **Telegram Bot** (Aiogram).

### 1️⃣ Backend API

```bash
# Из корня проекта
python run.py backend
```

- Запускается на `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs` (только в DEBUG режиме)
- Health check: `http://localhost:8000/health`

---

### 2️⃣ Telegram Bot

```bash
# Из корня проекта
python run.py bot
```

**Требования:**
- Backend API должен быть запущен (или указан `BACKEND_API_URL` в `.env`)
- Настроены переменные окружения:
  - `BOT_TOKEN` — токен Telegram бота
  - `BACKEND_API_URL` — URL Backend API (по умолчанию `http://localhost:8000`)
  - `REDIS_URL` — URL Redis сервера

---

## 📋 Переменные окружения

Создайте файл `.env` в корне проекта:

```env
# --- Common ---
DEBUG=True
REDIS_URL=redis://localhost:6379/0

# --- Backend ---
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
AUTO_MIGRATE=False

# --- Telegram Bot ---
BOT_TOKEN=your_bot_token_here
BACKEND_API_URL=http://localhost:8000
BACKEND_API_KEY=optional_api_key
BACKEND_API_TIMEOUT=10.0
```

---

## 🐳 Docker (TODO)

```bash
docker-compose up -d
```

---

## 🧪 Разработка

### Запуск через IDE (PyCharm/VSCode)

**Вариант 1:** Используйте `run.py` как entry point
- **Script path:** `C:\install\progect\Telegram_Bot_RPG\run.py`
- **Parameters:** `bot` или `backend`
- **Working directory:** `C:\install\progect\Telegram_Bot_RPG`

**Вариант 2:** Запуск модулей напрямую
```bash
# Backend
python -m uvicorn backend.main:app --reload

# Bot (добавьте корень в PYTHONPATH вручную)
python -m game_client.telegram_bot.app_telegram
```

---

## 📁 Структура проекта

```
Telegram_Bot_RPG/
├── run.py                  # Универсальный запускатель
├── backend/                # Backend API (FastAPI)
│   ├── main.py            # Entry point
│   ├── router.py          # Главный роутер
│   ├── domains/           # Бизнес-логика
│   └── ...
├── game_client/
│   └── telegram_bot/      # Telegram Bot клиент
│       ├── app_telegram.py  # Entry point
│       ├── core/
│       │   └── routers.py   # Реестр роутеров
│       └── features/        # Фичи (combat, arena, etc.)
├── common/                # Общий код (schemas, logger, etc.)
└── ...
```

---

## ❓ Troubleshooting

### `ModuleNotFoundError: No module named 'common'`

**Решение:** Всегда используйте `run.py` для запуска:
```bash
python run.py bot
```

Или запускайте из корня проекта:
```bash
python -m game_client.telegram_bot.app_telegram
```

---

### Backend недоступен

**Проверьте:**
1. Backend запущен: `python run.py backend`
2. URL правильный в `.env`: `BACKEND_API_URL=http://localhost:8000`
3. Health check работает: `curl http://localhost:8000/health`

---

## 📝 Следующие шаги

1. Настроить `.env` с вашими токенами
2. Запустить Backend: `python run.py backend`
3. Запустить Bot: `python run.py bot`
4. Протестировать `/start` команду в Telegram
