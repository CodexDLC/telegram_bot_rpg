# Redis Data Structure (RBC v2.0 Final)

## 1. Global Session State
**Root Pattern:** `combat:rbc:{sid}:*`

### 🌍 META (Hash)
**Key:** `...:meta`
* `active` (INT): 1 - бой идет, 0 - завершен.
* `step_counter` (INT): Глобальный счетчик событий.
* `active_actors` (INT): Количество живых участников (важно для авто-скейлинга задач).
* `teams` (JSON): `{ "red": [101], "blue": [202] }`.
* `actors_info` (JSON): `{ "101": "player", "202": "ai" }`.
* `dead_actors` (JSON): `[202]`.
* `winner` (STR): ID команды победителя (напр. "red", "blue").
* `rewards` (JSON): Итоговый лут и опыт (заполняется в конце).
* `start_time` (INT): Timestamp начала боя.
* `end_time` (INT): Timestamp завершения боя.
* `battle_type` (STR): Тип боя (pve, pvp).
* `mode` (STR): Режим (dungeon, arena, 1v1).
* `location_id` (STR): ID локации.

### 🛡 QUEUES & LOCKS
**Key:** `...:q:tasks` (LIST of JSON Strings)
* **Local Task Queue.** Хранит `CombatInteractionContext`.
* Строго FIFO.

**Key:** `...:sys:busy` (STRING)
* **Lock with TTL.**
* `SET ... NX EX 60`.
* Гарантирует, что только один воркер обрабатывает сессию в моменте.

### ⚔️ MOVES (ReJSON)
**Key:** `...:moves:{char_id}`
* `$.instant` (Array)
* `$.exchange` (Array)
* Удаляются только после успешного Commit.

### 📜 LOGS (List)
**Key:** `...:logs`
* Готовые логи для клиента.

---

## 2. Actor Namespace
**Pattern:** `combat:rbc:{sid}:actor:{char_id}:*`

| Суффикс | Тип | Описание |
| :--- | :--- | :--- |
| **`:state`** | **HASH** | **Hot Data.** `hp`, `en`, `tactics`, `afk_level`. |
| **`:raw`** | **ReJSON** | **Cold Data.** Атрибуты и статы. |
| **`:cache`** | **ReJSON** | **Calculated.** Кеш значений. |
| **`:effects`** | **ReJSON** | **Effects.** `[{id, expires_at_step}]`. |
| **`:data_xp`** | **ReJSON** | **Analytics.** `{"hits": 10}`. |
