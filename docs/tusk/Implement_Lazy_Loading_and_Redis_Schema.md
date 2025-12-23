# Архитектура Кэширования: Ядро, Сессии и Оркестрация

## 1. Концепция

Мы разделяем данные на **Персистентное Ядро** (хранится в `ac:{char_id}`) и **Временные Сессии** (хранятся в отдельных ключах).
Управление этим процессом осуществляет **GameStateOrchestrator**.

---

## 2. Структура Redis

### 2.1. Ядро (`ac:{char_id}`)
Хранит данные, которые всегда должны быть под рукой, и ссылки на активные сессии.
Соответствует таблицам `characters` и `character_stats`.

| Поле | Тип | Источник | Описание |
| :--- | :--- | :--- | :--- |
| **`state`** | String | `characters.game_stage` | Текущий игровой стейт (FSM). |
| **`location`** | JSON | `characters.location_id` | `{"current": "...", "prev": "..."}` |
| **`bio`** | JSON | `characters` | Имя, пол, дата создания. |
| **`stats`** | JSON | `character_stats` | Сила, Ловкость и т.д. |
| **`vitals`** | JSON | *Dynamic* | `{"hp": {"cur": 100, "max": 100}, ...}`. |
| **`combat_session_id`** | String | *Redis-only* | UUID активной сессии боя. |
| **`inventory_session_id`**| String | *Redis-only* | UUID активной сессии инвентаря. |
| **`scenario_session_id`** | String | *Redis-only* | UUID активной сессии сценария. |

### 2.2. Сессии (Session Keys)
Временные ключи, создаваемые профильными оркестраторами.

*   **`combat:session:{uuid}`**: Монстры, очередность ходов, логи.
*   **`inventory:session:{uuid}`**: Загруженный список предметов, фильтры.
*   **`scenario:session:{uuid}`**: Граф квеста, текущая нода, переменные.

---

## 3. GameStateOrchestrator

Главный класс, управляющий жизненным циклом данных.

### 3.1. Восстановление (`restore_full_state`)
*Вызывается при входе (Login) или потере кэша.*

1.  **Ядро:** Загружает данные из `characters` и `character_stats` в `ac:{char_id}`.
2.  **Контекст:** Проверяет поле `state` (из БД).
3.  **Делегирование:**
    *   Если `state == 'combat'`, вызывает `CombatOrchestrator.restore_session()`.
    *   Если `state == 'inventory'`, вызывает `InventoryOrchestrator.restore_session()`.
    *   И т.д.

### 3.2. Бэкап (`backup_full_state`)
*Вызывается при смене стейта или фоновым процессом.*

1.  **Ядро:** Сохраняет `bio`, `stats`, `state`, `location` в БД.
2.  **Сессии:** Проверяет наличие `*_session_id` в `ac:{char_id}`.
    *   Если есть ID, вызывает метод `backup_session(uuid)` у соответствующего оркестратора.
    *   Оркестратор сам решает, как сохранить свои данные (в JSON-поле, в таблицу истории и т.д.).

---

## 4. Фоновая Синхронизация (Background Worker)

Для защиты от сбоев (например, сервер упал, пока игрок в инвентаре) используется механизм "Dirty List".

1.  При любом изменении данных `char_id` добавляется в Redis Set `dirty_accounts`.
2.  Фоновый процесс (Celery/Task) раз в N минут:
    *   Берет ID из `dirty_accounts`.
    *   Вызывает `GameStateOrchestrator.backup_full_state(char_id)`.
    *   Удаляет ID из сета.

---

## 5. План Реализации

1.  **`GameStateOrchestrator`:** Реализовать методы `restore_full_state` и `backup_full_state` (пока только для Ядра).
2.  **Интеграция:** Внедрить вызов `restore` в `LoginService`.
3.  **Сессии:** Постепенно переводить `Combat`, `Inventory`, `Scenario` на модель сессий с методами `restore/backup`.
