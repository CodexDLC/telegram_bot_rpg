# 🧠 Redis Data Schema (RBC v3.1)

⬅️ [Назад](../README.md) | 🏠 [Документация](../../../../../README.md)

**Status:** Final
**Prefix:** `combat:rbc:{sid}:`

Эта схема описывает структуру хранения данных боевой сессии в Redis.
Используется RedisJSON для сложных структур и Hash для простых счетчиков.

---

## 1. Session Metadata
**Key:** `combat:rbc:{sid}:meta`
**Type:** `Hash`

Глобальные счетчики и состояние сессии.

| Field | Type | Description |
| :--- | :--- | :--- |
| `active` | `int` (0/1) | Флаг активности боя. |
| `step_counter` | `int` | Глобальный счетчик обработанных действий (для логов). |
| `active_actors_count` | `int` | Количество живых участников. |
| `teams` | `json` | Список команд: `{"blue": [101, 102], "red": [201]}`. |
| `winner` | `str` | Имя победившей команды (после завершения). |
| `actors_info` | `json` | Маппинг ID -> Type: `{"101": "player"}`. |
| `dead_actors` | `json` | Список ID мертвых: `[201]`. |
| `last_activity_at` | `int` | Timestamp последнего действия (для GC). |
| `battle_type` | `str` | Тип боя (PvE, PvP). |
| `location_id` | `str` | ID локации. |

---

## 2. Actor Data (The Big JSON)
**Key:** `combat:rbc:{sid}:actor:{id}`
**Type:** `JSON` (RedisJSON)

Единый объект состояния персонажа. См. [Actor Model](./actor_model.md).

```json
{
  "meta": { "id": 101, "hp": 100, "en": 50, "team": "blue", ... },
  "raw": { "attributes": {...}, "modifiers": {...} },
  "skills": { "skill_swords": 0.5 },
  "loadout": { "layout": {...}, "belt": [...], "tags": [...] },
  "active_abilities": [...],
  "xp_buffer": {...},
  "metrics": {...},
  "explanation": {...}
}
```

---

## 3. Targeting Queues
**Key:** `combat:rbc:{sid}:targets:{id}`
**Type:** `List` (Redis List)

Очередь доступных целей для персонажа `{id}`.
Используется для **Exchange** стратегии.

*   Содержит ID врагов (`[201, 202]`).
*   `LPOP` забирает цель для атаки.
*   Если очередь пуста, атаковать нельзя (нужно ждать или бить другого).

---

## 4. Moves Buffer (Intents)
**Key:** `combat:rbc:{sid}:moves:{id}`
**Type:** `JSON` (RedisJSON)

Буфер заявленных действий (Intents) от игрока `{id}`.
Заполняется `CombatTurnManager`. Читается и очищается `CombatCollector`.

**Structure:** Dictionary grouped by strategy.

```json
{
  "exchange": {
    "a1b2c3d4": {
      "move_id": "a1b2c3d4",
      "char_id": 101,
      "strategy": "exchange",
      "payload": { "target_id": 201, "skill_id": "heavy_strike" }
    }
  },
  "item": {
    "e5f6g7h8": {
      "move_id": "e5f6g7h8",
      "strategy": "item",
      "payload": { "item_id": 55 }
    }
  },
  "instant": {}
}
```

---

## 5. Event Log (History)
**Key:** `combat:rbc:{sid}:log`
**Type:** `List` (Redis List)

Хронологический лог событий боя.
Используется для отправки клиенту и аналитики.

**Structure:** JSON strings (`CombatLogEntryDTO`).

```json
{
  "text": "Hero hits Orc for 10 damage.",
  "timestamp": 1715000005.0,
  "tags": ["damage", "crit"]
}
```

---

## 6. ARQ Queues (Job System)
**Key:** `arq:queue` (Global)

Очереди задач для воркеров.

*   `combat_collector_task`: Сборка мувов (Immediate & Timeout).
*   `combat_action_task`: Выполнение действия (Pipeline).
*   `combat_ai_task`: Ход бота.
