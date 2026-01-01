# Actor Manager Design (Combat Repository)

## Роль
`ActorManager` эволюционировал из простого хелпера в полноценный **Репозиторий Боя (Combat Repository)**.
Его задача — абстрагировать сложную структуру хранения в Redis (папки, JSON, Hash) и предоставлять бизнес-логике (Executor, Orchestrator) удобные Python-объекты (Context).

---

## Интерфейс

### 1. `load_session_context(session_id) -> CombatSessionContext`
**Назначение:** Полная загрузка состояния боя для обработки тика.
**Алгоритм:**
1.  **Get Meta:** Загружает `combat:rbc:{sid}:meta`.
2.  **Parse Actors:** Извлекает список `char_id` из поля `actors_info`.
3.  **Pipeline Fetch (Batch):**
    *   Для каждого актора добавляет в пайплайн команды:
        *   `HGETALL ...:actor:{id}:state` (HP, En, Tactics)
        *   `JSON.GET ...:actor:{id}:cache` (Stats)
        *   `JSON.GET ...:actor:{id}:effects` (Active Effects)
4.  **Assembly:** Собирает результаты в объекты `CombatActorContext` и упаковывает в `CombatSessionContext`.

### 2. `commit_session_changes(session_id, context, logs)`
**Назначение:** Атомарное сохранение изменений после обработки тика.
**Алгоритм:**
1.  **Pipeline Build:**
    *   Обновляет `meta:step_counter`.
    *   Для каждого измененного актора:
        *   `HSET ...:state` (новые HP, En).
        *   `JSON.SET ...:effects` (если эффекты изменились).
    *   `RPUSH ...:logs` (добавляет новые логи).
2.  **Execute:** Отправляет всё одной пачкой.

---

## Структура Данных (In-Memory DTO)

### `CombatActorContext`
```python
@dataclass
class CombatActorContext:
    char_id: int
    hp: int
    energy: int
    tactics: int
    stats: Dict[str, float]      # Read-Only (из кэша)
    effects: List[Dict]          # Mutable (активные эффекты)
    tokens: Dict[str, int]       # Mutable (комбо-поинты)
```

### `CombatSessionContext`
```python
@dataclass
class CombatSessionContext:
    session_id: str
    step_counter: int
    meta: Dict[str, Any]
    actors: Dict[int, CombatActorContext] # Все участники боя
```

---

## Почему это круто?
1.  **1 RTT Read / 1 RTT Write:** Максимальная эффективность сети. Мы не бегаем в Redis за каждым чихом.
2.  **Strong Consistency:** Вся логика работает с одним и тем же слепком данных. Нет ситуации, когда HP прочитали в начале, а Энергию в конце, и они рассинхронизировались.
3.  **Testability:** `CombatSessionContext` легко замокать в юнит-тестах, не поднимая реальный Redis.
