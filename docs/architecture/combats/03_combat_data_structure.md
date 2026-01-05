# Combat Data Structure (RBC v3.0)

**Storage:** Redis (Cluster/Standalone)
**Key Prefix:** `combat:rbc:{session_id}`

---

## 1. Global Session Data

### 1.1. META (RedisHash)
**Key:** `...:meta`
**TTL:** 24h (History)

| Field | Type | Description |
| :--- | :--- | :--- |
| `active` | int (0/1) | Флаг активности боя. |
| `step_counter` | int | Глобальный счетчик обработанных действий (для синхронизации логов). |
| `start_time` | int | Timestamp начала боя. |
| `last_activity_at` | int | Timestamp последней активности (для Chaos Protocol / Garbage Collector). |
| `teams` | json | Структура команд: `{"red": [101, 102], "blue": [201]}`. |
| `actors_info` | json | Типы участников: `{"101": "player", "201": "ai"}`. |
| `dead_actors` | json | Список мертвых: `[201]`. (Кэш для быстрого резолвинга целей). |
| `alive_counts` | json | Счетчики живых по командам: `{"red": 2, "blue": 1}`. |
| `battle_type` | str | "pvp", "pve", "raid". |
| `location_id` | str | ID локации (для визуализации). |

### 1.2. TARGETS (RedisJSON)
**Key:** `...:targets`
**Structure:** Graph (Adjacency List)
Очереди целей для каждого участника.

```json
{
  "101": [201, 202],  // Игрок 101 хочет бить 201, потом 202
  "201": [101]        // Бот 201 хочет бить 101
}
```

### 1.3. QUEUE (RedisList)
**Key:** `...:q:actions`
**Content:** Serialized `CombatActionDTO`.
Системная очередь задач для Исполнителя.

### 1.4. LOG (RedisList)
**Key:** `...:log`
**Content:** JSON Log Entries.
История боя для клиента.

### 1.5. BUSY (RedisString / JSON)
**Key:** `...:sys:busy`
**Content:** "pending" | "worker_uuid"
Fencing Token для синхронизации воркеров.

---

## 2. Actor Data (Namespace)

**Key Prefix:** `...:actor:{char_id}`

### 2.1. STATE (RedisHash) - Hot Data
Изменяемые параметры, требующие атомарных инкрементов (HINCRBY).

| Field | Type | Description |
| :--- | :--- | :--- |
| `hp` | int | Текущее здоровье. |
| `max_hp` | int | Максимальное здоровье (Snapshot). |
| `en` | int | Энергия. |
| `max_en` | int | Макс. энергия. |
| `tactics` | int | Очки тактики. |
| `afk_level` | int | Уровень AFK (0-3). |
| `is_dead` | int (0/1) | Флаг смерти. |
| `tokens` | json | Боевые токены: `{"gift": 1, "parry": 1}`. |

### 2.2. RAW (RedisJSON) - Cold Data
Статичные (в рамках раунда) параметры. Математическая модель.

```json
{
  "attributes": {"str": 10, "agi": 5},
  "modifiers": {"phys_dmg": 1.5},
  "temp": {}, // Временные модификаторы (баффы на 1 ход)
  "name": "Hero Name",
  "is_player": true
}
```

### 2.3. LOADOUT (RedisJSON) - Config
Экипировка и доступные скиллы.

```json
{
  "equipment_layout": {"main_hand": "sword"},
  "known_abilities": ["strike", "fireball"]
}
```

### 2.4. META (RedisJSON) - Static Info
Имя, тип, аватар.

```json
{
  "name": "Hero",
  "type": "player",
  "team": "red"
}
```

### 2.5. ACTIVE ABILITIES (RedisJSON) - Dynamic Modifiers
Список активных эффектов (баффы/дебаффы).

```json
[
  {
    "uid": "uuid",
    "ability_id": "poison",
    "source_id": 201,
    "expire_at_exchange": 5,
    "impact": {"hp": -10}
  }
]
```

### 2.6. DATA XP (RedisJSON) - Accumulator
Накопленный опыт и статистика.

```json
{
  "xp_gained": 100,
  "damage_dealt": 500
}
```

---

## 3. Moves (Intents)

**Key:** `...:moves:{char_id}` (RedisJSON)
Буфер намерений игрока.

```json
{
  "exchange": {
    "uuid_1": { ...CombatMoveDTO... }
  },
  "item": {},
  "instant": {}
}
```
