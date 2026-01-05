# Combat Initialization (RBC v2.0)

**Role:** Создание и настройка боевой сессии.
**Service:** `CombatEntryOrchestrator` (Init Service).

---

## 1. Входные данные
*   **Mode:** Тип боя (`standard`, `arena`, `shadow`).
*   **Teams:** Конфигурация команд (кто за кого).
    *   `blue`: `[player_101, player_102]`
    *   `red`: `[monster_orc_1, monster_orc_2]`

---

## 2. Логика Оркестратора (`CombatEntryOrchestrator`)

1.  **Создание сессии**: Генерируется уникальный `session_id` (UUID).
2.  **Создание записи боя**: Вызывается `lifecycle.create_battle` с параметрами режима.
3.  **Обработка команд**:
    *   Команды распределяются по цветам: `blue` (0), `red` (1), `green` (2), `yellow` (3).
    *   **Игроки**: Добавляются через `lifecycle.add_participant`.
    *   **Монстры**: Добавляются через `lifecycle.add_db_monster_participant` (с отрицательными ID).
4.  **Инициализация состояния**:
    *   `lifecycle.initialize_battle_state`: Расчет целей, зарядов тактики.
    *   **Target Graph Initialization:** Заполняет ключ `combat:rbc:{sid}:targets`.
        *   Для каждого участника создает список врагов (из противоположных команд).
        *   **Shuffle:** Список врагов перемешивается (`random.shuffle`), чтобы сломать предсказуемость начального фокуса.
    *   `lifecycle.initialize_exchange_queues`: Наполнение очередей обмена ударами (пустыми списками).
    *   **System Heartbeat (Важно):** Устанавливаем в `combat:rbc:{sid}:meta` поле `last_activity_ts = current_timestamp`.
5.  **Возврат результата**:
    *   Возвращается **Boolean** (`True` / `False`) или простой словарь `{"success": True, "session_id": "..."}`.

---

## 3. Redis Structure (Initial State)

После инициализации в Redis должны появиться:
*   `combat:rbc:{sid}:meta` (Active=1, Teams, StartTime, LastActivity).
*   `combat:rbc:{sid}:targets` (JSON Graph: `{ "101": [202, 201] }` - Shuffled).
*   `combat:rbc:{sid}:actor:{id}:state` (HP, EN).
*   `combat:rbc:{sid}:actor:{id}:raw` (Stats Source).
*   `combat:rbc:{sid}:moves:{id}` (Empty JSON: `{"item":[], "instant":[], "exchange":[]}`).
