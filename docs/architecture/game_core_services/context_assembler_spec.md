# Technical Spec: ContextAssembler (Bulk Data Aggregator)

**Тип:** Core Module / Orchestrator
**Роль:** Превращает списки ID в списки Redis-ключей с готовыми снапшотами.
**Ключевая фича:** Batch Processing (оптимизация запросов к БД).

---

## 1. Концепция
**ContextAssembler** — это изолированный модуль, который занимается только подготовкой контекста. Он не знает про бой, торговлю или туториал. Он просто конвертер `ID -> RedisKey`.

**Принципы:**
1.  **Bulk Operations:** Всегда работает со списками ID. Использует `WHERE id IN (...)` для минимизации запросов к БД.
2.  **Strategy Pattern:** Использует разные стратегии сборки (`PlayerAssembler`, `MonsterAssembler`) под единым интерфейсом.
3.  **Zero Coupling:** Не зависит от логики потребителя.

---

## 2. Структура Модуля
```plaintext
apps/game_core/context_assembler/
├── logic/                     <-- Папка для стратегий сборки
│   ├── __init__.py
│   ├── base_assembler.py      <-- Абстрактный класс (Interface)
│   ├── player_assembler.py    <-- Логика для SQL (Players)
│   ├── monster_assembler.py   <-- Логика для SQL (Generated Monsters)
│   └── pet_assembler.py       <-- Логика для петов
│
├── service.py                 <-- ContextAssemblerOrchestrator (Facade)
├── dtos.py                    <-- Входные и выходные форматы
└── interface.py               <-- Интерфейс для Роутера
```

---

## 3. Контракт (API)

### Input (Request)
```json
{
  "player": [101, 102],     // Список ID игроков
  "monster": [505, 506],    // Список ID мобов
  "pet": [20]               // Список ID петов
}
```

### Output (Response)
```json
{
  "player": {
    "101": "temp:setup:uuid-player-1",
    "102": "temp:setup:uuid-player-2"
  },
  "monster": {
    "505": "temp:setup:uuid-mob-1",
    "506": "temp:setup:uuid-mob-2"
  },
  "pet": {
    "20": "temp:setup:uuid-pet-1"
  }
}
```

---

## 4. Логика Работы (Orchestrator)

### `ContextAssemblerOrchestrator.prepare_bulk_context`
1.  **Fan-Out:** Принимает словарь `{"type": [ids]}`.
2.  Для каждого типа находит соответствующий `Assembler` (Strategy).
3.  Запускает `assembler.process_batch(ids)` асинхронно (собирает таски).
4.  **Gather:** Ждет выполнения всех тасков.
5.  **Result:** Собирает результаты в итоговый словарь.

### `PlayerAssembler.process_batch` (Пример Стратегии)
1.  **DB Query:** Делает **один** запрос к БД: `SELECT * FROM chars WHERE id IN (101, 102)`.
2.  **Transform:** В цикле (CPU-bound) преобразует ORM-объекты в JSON (Action-Based Strings).
3.  **Redis Pipeline:** Генерирует UUID для каждого и сохраняет в Redis пачкой (или параллельно).
4.  **Return:** Возвращает маппинг `{id: key}`.

---

## 5. Потребление (Use Case: Combat)

```python
# CombatOrchestrator
async def start_combat(self, red_ids, blue_ids):
    # 1. Запрос ключей
    keys = await context_assembler.prepare_bulk_context({
        "player": red_ids,
        "monster": blue_ids
    })
    
    # 2. Распределение по командам (Бизнес-логика)
    session_data = {
        "teams": {
            "red": [keys["player"][uid] for uid in red_ids],
            "blue": [keys["monster"][uid] for uid in blue_ids]
        }
    }
    
    # 3. Старт сессии
    return await combat_manager.create_session(session_data)
```
