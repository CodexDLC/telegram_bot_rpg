# Combat Gateway Specification (Unified Router)

**Role:** Единая точка входа для всех запросов к боевой системе (кроме инициализации).
**Class Name:** `CombatGateway`
**Responsibility:** Маршрутизация запросов (CQRS), Валидация сессии, Time-Stamping, Создание "Пули", Чтение данных.

---

## 1. Interface (Public Methods)

### A. CoreRouter Adapter (System Entry Point)
**Method:** `get_entry_point(action: str, context: dict) -> Any`
**Назначение:** Стандартный интерфейс для вызова из `CoreRouter` (межмодульное взаимодействие).
**Поддерживаемые действия:**
*   `get_snapshot`: Получить дашборд.
*   `get_logs`: Получить логи.

### B. Command (Write) - Direct Call
**Method:** `submit_move(char_id: int, action_type: str, payload: dict) -> CombatDashboardDTO`
**Назначение:** Регистрация действия игрока.
**Возвращает:** Актуальный `CombatDashboardDTO` (сразу после постановки задачи в очередь).

**Поддерживаемые Action Types:**
1.  `attack`: Стандартный удар (требует `attack_zones`, `block_zones`).
2.  `use_item`: Использование предмета (требует `item_id`).
3.  `switch_target`: Смена цели (требует `target_id`).
    *   *Логика:* Проверяет `state.tactics > 0`. Если да — меняет порядок ID в очереди `moves:exchange` (или просто обновляет мета-данные таргетинга). Списывает 1 тактику.

### C. Query (Read) - Direct Call
**Method:** `get_data(char_id: int, request_type: str, params: dict) -> Any`
**Назначение:** Получение данных без изменения стейта.

---

## 2. Zone Validation Policy (Anti-Cheat)
Бекенд не доверяет клиенту, но и не пытается "угадать" за него.

**Правила:**
1.  **Empty Check:** Если прислано 0 зон атаки или блока — **Error** ("Выберите зоны").
2.  **Overflow Check:** Если прислано больше зон, чем разрешено (например, 3 зоны атаки вместо 1):
    *   Бекенд **НЕ** возвращает ошибку.
    *   Бекенд выбирает **случайную** зону из присланных (`random.choice(zones)`).
    *   *Почему:* Это делает попытки "хакнуть" клиент бессмысленными (ты не получишь преимущества удара по всем зонам), но не ломает игру из-за лагов UI.

---

## 3. Signaling (Double Trigger)
Мы отказываемся от пассивного ожидания в пользу активных сигналов.

При каждом `submit_move` Роутер отправляет **ДВА** сигнала в очередь `arq:combat_collector`:

### Signal 1: `check_immediate`
*   **Delay:** 0 (Мгновенно).
*   **Задача:** "Проверь, не ждет ли меня уже кто-то?".
*   **Действие Колектора:** Ищет пару. Если нашел — создает `Exchange Action`.

### Signal 2: `check_timeout`
*   **Delay:** `TIMEOUT_SECONDS` (например, 60 сек).
*   **Задача:** "Если я все еще здесь через минуту — заставь меня ударить".
*   **Действие Колектора:**
    *   Проверяет, существует ли еще этот `move_id` в Redis.
    *   Если **НЕТ** (уже сыграл в паре) — игнорирует сигнал (No Op).
    *   Если **ДА** — создает `Forced Action` (удар по спящему).
