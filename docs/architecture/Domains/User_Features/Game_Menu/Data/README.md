# 💾 Data Layer

⬅️ [Back to Game Menu](../README.md)

## 1. Data Sources (Источники данных)

### 1.1. HUD Data (Vitals & State)
Данные для отображения состояния персонажа (HP, Energy, Location) берутся из **Redis** ("Hot Data").
Это обеспечивает мгновенный доступ без нагрузки на PostgreSQL.

*   **Source:** `AccountManager`
*   **Reference:** [Account Manager Docs](../../../../Infrastructure/redis/manager/Account_Manager.md)
*   **Redis Key:** `ac:{char_id}`
*   **DTO File:** `common/schemas/account_context.py` (Использовать `AccountContextDTO`, `StatsDict`)
*   **Required Fields:**
    *   `$.stats.hp` (`cur`, `max`, `regen`)
    *   `$.stats.energy` (`cur`, `max`, `regen`)
    *   `$.stats.last_update` (Timestamp последнего пересчета регенерации) — **Критично для актуализации данных.**

### 1.2. Buttons Configuration
Конфигурация доступных кнопок (какие кнопки показывать в каком стейте) определяется логикой сервиса, но сами тексты и иконки хранятся в ресурсах.

*   **File:** [Resources](./Resources.md)
