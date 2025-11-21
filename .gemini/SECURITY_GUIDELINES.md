# Security Guidelines

1.  **SQL Injection:**
    * Запрещены "сырые" SQL-запросы с форматированием строк (f-strings).
    * Только методы SQLAlchemy ORM (`select`, `update`, `insert`) с параметризацией.

2.  **Data Validation:**
    * Любой JSON из БД должен валидироваться через Pydantic DTO перед использованием.
    * Не доверяем содержимому `item_data` без проверки схемы.

3.  **Telegram Security:**
    * Всегда проверяй `call.from_user` на наличие.
    * Всегда проверяй права доступа (владелец предмета `character_id` должен совпадать с `user_id` сессии).

4.  **Sensitive Data:**
    * Никаких токенов или паролей в коде. Только `app/core/config.py` и `.env`.