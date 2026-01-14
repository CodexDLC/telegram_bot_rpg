# 🔑 Redis Key Schema Registry

⬅️ [Назад](README.md)

> **Source:** `apps/common/services/redis/redis_key.py`

Этот документ служит центральным реестром всех неймспейсов Redis, чтобы избежать коллизий.

## 1. Combat System (RBC v3.0)
**Prefix:** `combat:rbc:{sid}:*`
*   `...:meta` (Hash) — Метаданные боя.
*   `...:actor:{cid}` (Hash) — Состояние актера.
*   `...:moves:{cid}` (JSON) — Заявленные ходы.
*   `...:targets` (JSON) — Очереди целей.
*   `...:q:actions` (List) — Очередь задач для воркера.
*   `...:log` (List) — Логи боя.

## 2. Session Data
**Prefix:** `*:session:{cid}:*`
*   `scen:session:{cid}:data` (Hash) — Данные сценария.
*   `inv:session:{cid}:data` (Hash) — Данные инвентаря.
*   `lobby_session:{uid}` (JSON) — Данные лобби.

## 3. World & Locations
**Prefix:** `world:*`
*   `world:loc:{loc_id}` (Hash) — Метаданные локации.
*   `world:players_loc:{loc_id}` (Set) — Игроки в локации.

## 4. Arena & Matchmaking
**Prefix:** `arena:*`
*   `arena:queue:{mode}:zset` (ZSet) — Очередь поиска.
*   `arena:req:{cid}` (Hash) — Заявка игрока.

## 5. Player Status
**Prefix:** `player:*`
*   `player:status:{cid}` (String) — Текущий статус (Idle, Combat, Trade).

## 6. Legacy (To Be Removed)
*   `combat:sess:*` — Старая боевая система.
*   `ac:{cid}` — Старый аккаунт.
*   `s_d:*`, `g_d:*` — Старые данжи.
