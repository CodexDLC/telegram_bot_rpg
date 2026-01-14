# 📝 Logging System

⬅️ [Назад](README.md)

> **Source:** `apps/common/core/loguru_setup.py`

Мы используем библиотеку **Loguru** вместо стандартного `logging`.

## 🚀 Features
1.  **InterceptHandler:** Перехватывает логи от стандартных библиотек (`aiogram`, `sqlalchemy`) и направляет их в Loguru.
2.  **Sinks (Стоки):**
    *   **Console:** Цветной вывод для разработки.
    *   **File (`debug.log`):** Полный лог с ротацией (zip).
    *   **JSON (`errors.json`):** Структурированный лог ошибок для аналитики.

## 🛠️ Usage
```python
from loguru import logger as log

log.info("UserAction | user_id=123 action=attack")
log.error("SystemError | component=Redis reason='Connection failed'", exc_info=True)
```
Мы придерживаемся формата `Context | key=value` для удобства грепа.
