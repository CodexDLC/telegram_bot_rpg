# ⚙️ Configuration

⬅️ [Назад](./README.md)

> **Source:** `apps/common/core/settings.py`

Мы используем `pydantic-settings` для управления конфигурацией.
Все настройки читаются из файла `.env` в корне проекта.

## 🔑 Environment Variables

### Critical
*   `BOT_TOKEN` — Токен Telegram бота.
*   `GEMINI_TOKEN` — Токен Google Gemini AI.

### Database
*   `DATABASE_URL` — Строка подключения (PostgreSQL).
*   `DB_SSL_REQUIRE` — `True` для облака (Neon), `False` для локального Docker.

### Redis
*   `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`.

### Logging
*   `LOG_LEVEL_CONSOLE` — Уровень логов в консоли (DEBUG/INFO).
*   `LOG_LEVEL_FILE` — Уровень логов в файле.
*   `LOG_ROTATION` — Размер файла ротации (например, "10 MB").

### Game Settings
*   `ADMIN_IDS` — Список ID администраторов (через запятую).
*   `SYSTEM_USER_ID` — ID системного пользователя (для служебных операций).
