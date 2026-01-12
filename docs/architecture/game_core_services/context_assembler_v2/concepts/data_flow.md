# Data Flow: Request Processing Chain

⬅️ [Назад к Concepts](./README.md) | 🏠 [Назад к Context Assembler v2](../README.md)

Этот документ описывает полный жизненный цикл запроса к Context Assembler v2 от момента вызова до получения Redis-ключей.

---

## Общая схема (High-Level)

```mermaid
graph TD
    A[Заказчик (Combat/Status/Inventory)] -->|Request| B[CoreRouter]
    B -->|Route| C[ContextAssemblerOrchestrator]
    C -->|Parallel Tasks| D[PlayerAssembler]
    C -->|Parallel Tasks| E[MonsterAssembler]
    D -->|Scope| F[Query Plan Builder]
    F -->|Table List| G[Database (Batch Queries)]
    G -->|Raw Data| H[Formatters (Logic Layer)]
    H -->|Formatted Data| I[Temp DTO Assembly]
    I -->|JSON| J[Redis Storage]
    J -->|UUID Keys| K[Response]
```

---

## Step-by-Step Breakdown

### Step 0: Request Initiation (Заказчик)
**Кто:** `CombatEntryOrchestrator`, `StatusService`, `InventoryService` или любой другой модуль
**Что делает:**
Формирует запрос с указанием:
1.  Список ID сущностей (игроки, монстры)
2.  Scope (для чего нужны данные)

**Пример:**
```python
# Combat System запрашивает данные для боя
request = ContextRequestDTO(
    player_ids=[101, 102],
    monster_ids=["uuid-mob-1", "uuid-mob-2"],
    scope="combats"
)
```

**Куда отправляет:**
Через `CoreRouter` в модуль `context_assembler`
```python
response = await core_router.route(
    module="context_assembler",
    action="assemble",
    context=request.model_dump()
)
```

### Step 1: Routing (CoreRouter)
**Кто:** `CoreRouter` (система межмодульной коммуникации)
**Что делает:**
1.  Находит модуль `context_assembler`
2.  Вызывает его entry point метод `get_entry_point`

**Код:**
```python
# Внутри CoreRouter
module = self.modules["context_assembler"]
result = await module.get_entry_point(
    action="assemble",
    context=request_dict
)
```
**Передаёт управление:** `ContextAssemblerOrchestrator`

### Step 2: Orchestration (ContextAssemblerOrchestrator)
**Кто:** `ContextAssemblerOrchestrator` (главный фасад)
**Что делает:**

**2.1. Парсинг запроса**
```python
request = ContextRequestDTO(**context)
# Извлекает: player_ids, monster_ids, scope
```

**2.2. Определение стратегий**
```python
# Если есть player_ids → нужен PlayerAssembler
# Если есть monster_ids → нужен MonsterAssembler
# Если есть pet_ids → нужен PetAssembler (будущее)
```

**2.3. Формирование задач**
```python
tasks = []
task_mapping = []

if request.player_ids:
    task = player_assembler.process_batch(
        ids=request.player_ids,
        scope=request.scope
    )
    tasks.append(task)
    task_mapping.append("player")

if request.monster_ids:
    task = monster_assembler.process_batch(
        ids=request.monster_ids,
        scope=request.scope
    )
    tasks.append(task)
    task_mapping.append("monster")
```

**2.4. Параллельное выполнение**
```python
results = await asyncio.gather(*tasks)
```
Все Assemblers работают параллельно. Если запрошены 10 игроков и 5 монстров, оба batch-запроса идут одновременно.

**2.5. Сборка ответа**
```python
response = ContextResponseDTO()

for entity_type, (success_map, errors) in zip(task_mapping, results):
    if entity_type == "player":
        response.player = success_map
        response.errors["player"] = errors
    elif entity_type == "monster":
        response.monster = success_map
        response.errors["monster"] = errors

return response
```

**Результат:**
```python
{
    "player": {101: "temp:setup:uuid-1", 102: "temp:setup:uuid-2"},
    "monster": {"uuid-mob-1": "temp:setup:uuid-3"},
    "errors": {"player": [], "monster": []}
}
```

### Step 3: Strategy Execution (PlayerAssembler)
**Кто:** `PlayerAssembler` (стратегия для игроков)
**Что делает:**

**3.1. Построение плана запросов**
```python
query_plan = self._build_query_plan(scope)
# scope="combats" → ["attributes", "inventory", "skills", "vitals", "symbiote"]
# scope="status" → ["attributes", "vitals", "symbiote"]
```

**Логика Query Plan Builder:**
```python
QUERY_PLANS = {
    "combats": ["attributes", "inventory", "skills", "vitals", "symbiote"],
    "status": ["attributes", "vitals", "symbiote"],
    "inventory": ["inventory", "wallet"],
}

def _build_query_plan(scope: str):
    return QUERY_PLANS.get(scope, QUERY_PLANS["combats"])
```

**3.2. Выполнение запросов к БД**
```python
tasks = []
task_mapping = []

if "attributes" in query_plan:
    tasks.append(self.attributes_repo.get_attributes_batch(ids))
    task_mapping.append("attributes")

if "inventory" in query_plan:
    tasks.append(self.inv_repo.get_items_by_location_batch(ids, "equipped"))
    task_mapping.append("inventory")

if "skills" in query_plan:
    tasks.append(self.skill_repo.get_all_skills_progress_batch(ids))
    task_mapping.append("skills")

if "vitals" in query_plan:
    tasks.append(self.account_manager.get_accounts_json_batch(ids, "vitals"))
    task_mapping.append("vitals")

if "symbiote" in query_plan:
    tasks.append(self.symbiote_repo.get_symbiotes_batch(ids))
    task_mapping.append("symbiote")

# Параллельное выполнение всех запросов
results = await asyncio.gather(*tasks)
```
**Важно:** Все запросы к БД идут параллельно через `asyncio.gather`. Это один RTT вместо пяти последовательных.

**3.3. Сборка сырых данных**
```python
raw_data = {}
for key, result in zip(task_mapping, results):
    raw_data[key] = result

# Результат:
# {
#     "attributes": [AttributesDTO(char_id=101, str=15, ...), ...],
#     "inventory": {101: [ItemDTO(...), ItemDTO(...)], 102: [...]},
#     "skills": {101: [SkillDTO(...), ...], 102: [...]},
#     "vitals": [{...}, {...}],  # в порядке ids
#     "symbiote": [SymbioteORM(...), ...]
# }
```

**3.4. Форматирование (пока заглушка)**
```python
formatted_data = await self._format_data(raw_data, scope)
# TODO: Реализовать Formatters Layer
# Пока просто возвращаем raw_data как есть
```

**3.5. Сборка Temp DTO**
```python
contexts = {}

for char_id in ids:
    # Извлекаем данные для конкретного персонажа из raw_data
    char_data = self._extract_char_data(char_id, formatted_data)
    
    # Выбираем класс DTO на основе scope
    dto_class = self._select_dto_class(scope)
    # scope="combats" → CombatTempContext
    # scope="status" → StatusTempContext
    
    try:
        # Создаём экземпляр DTO
        context_schema = dto_class(**char_data)
        
        # Pydantic автоматически вызовет computed_field методы
        # CombatTempContext → math_model, loadout, vitals
        # StatusTempContext → stats_display, vitals_display
        
        # Сериализуем в dict с алиасами
        # ВАЖНО: exclude_none=True убирает core_* поля, которые не нужны в Redis
        context_data = context_schema.model_dump(by_alias=True, exclude_none=True)
        
        contexts[char_id] = context_data
    except Exception as e:
        log.error(f"Failed to assemble context for {char_id}: {e}")
        continue  # Пропускаем этот ID, не ломаем весь batch
```

**Пример context_data для scope=combats (ТОЛЬКО проекции):**
```python
{
    "math_model": {  # alias для combat_view
        "attributes": {"strength": {"base": "15", "flats": {}, "percents": {}}},
        "modifiers": {"physical_damage_min": {"sources": {"item:sword": "+25"}}}
    },
    "loadout": {  # alias для loadout_view
        "belt": [...],
        "abilities": ["strike", "heavy_blow"],
        "skills": []
    },
    "vitals": {  # alias для vitals_view
        "hp_current": 100,
        "energy_current": 50
    },
    "meta": {  # alias для meta_view
        "entity_id": 101,
        "type": "player",
        "name": "Hero"
    }
}
```

**3.6. Сохранение в Redis**
```python
success_map = {}
contexts_to_save = {}

for char_id, context_data in contexts.items():
    redis_key = f"temp:setup:{uuid.uuid4()}"
    success_map[char_id] = redis_key
    contexts_to_save[char_id] = (redis_key, context_data)

# Массовое сохранение через Pipeline
await self.context_manager.save_context_batch(contexts_to_save)
```

**Redis операция:**
```python
# Внутри ContextRedisManager
async with self.redis.pipeline() as pipe:
    for char_id, (key, data) in contexts_to_save.items():
        pipe.json().set(key, "$", data)
        pipe.expire(key, 3600)  # TTL 1 час
    await pipe.execute()
```

**3.7. Возврат результата**
```python
return success_map, error_list
# success_map = {101: "temp:setup:uuid-1", 102: "temp:setup:uuid-2"}
# error_list = []  # ID, которые не удалось обработать
```

### Step 4: Monster Strategy (MonsterAssembler)
**Кто:** `MonsterAssembler` (стратегия для монстров)
**Что делает:**

**4.1. Запрос к БД**
```python
monsters_orm = await self.monster_repo.get_monsters_batch(str_ids)
# Один запрос: SELECT * FROM generated_monsters WHERE id IN (...)
```

**4.2. Трансформация**
```python
for monster_orm in monsters_orm:
    # Используем MonsterTempContextSchema
    context_schema = MonsterTempContextSchema(
        core_stats=monster_orm.scaled_base_stats,
        core_loadout=monster_orm.loadout_ids,
        core_skills=monster_orm.skills_snapshot,
        core_meta={
            "id": str(monster_orm.id),
            "name": monster_orm.name_ru,
            "role": monster_orm.role,
            "threat": monster_orm.threat_rating
        }
    )
    
    context_data = context_schema.model_dump(by_alias=True, exclude_none=True)
    contexts[monster_id] = context_data
```
**Особенность:** У монстров данные уже лежат в JSON-полях таблицы (`scaled_base_stats`, `loadout_ids`). Не нужно джойнить несколько таблиц как для игроков.

**4.3. Сохранение и возврат**
Аналогично `PlayerAssembler` — UUID ключи в Redis.

### Step 5: Response Assembly (Orchestrator)
**Кто:** `ContextAssemblerOrchestrator` (возврат управления)
**Что делает:**
Собирает результаты всех Assemblers в единый ответ.
```python
response = ContextResponseDTO(
    player={101: "temp:setup:uuid-1", 102: "temp:setup:uuid-2"},
    monster={"uuid-mob-1": "temp:setup:uuid-3"},
    errors={"player": [], "monster": []}
)
```

### Step 6: Return to Consumer (CoreRouter)
**Кто:** `CoreRouter`
**Что делает:**
Возвращает response заказчику.
```python
# Внутри CombatEntryOrchestrator
response = await core_router.route("context_assembler", "assemble", {...})

# Теперь есть Redis-ключи для каждого участника
player_keys = response.player  # {101: "temp:setup:uuid-1", ...}
monster_keys = response.monster  # {"uuid-mob-1": "temp:setup:uuid-3"}
```

### Step 7: Usage (Заказчик использует ключи)
**Пример: Combat System**
```python
# 1. Получили ключи
keys = response.player

# 2. Используем их для создания боя
session_data = {
    "teams": {
        "red": [keys[101], keys[102]],  # UUID-ключи игроков
        "blue": [monster_keys["uuid-mob-1"]]
    }
}

# 3. Combat System читает данные из Redis по этим ключам
# В Redis лежит готовая math_model, loadout и vitals.
await combat_manager.create_session(session_data)
```

**Пример: Status Screen**
```python
# 1. Получили ключ
key = response.player[101]  # "temp:setup:uuid-1"

# 2. Читаем данные
context = await redis.json().get(key)

# 3. Используем computed fields (готовые проекции)
stats = context["stats_display"]  # Форматированные статы
vitals = context["vitals_display"]  # HP/Energy бары

# 4. Показываем UI
await show_status_screen(stats, vitals)
```

---

## Optimization Points (Точки оптимизации)

### Параллелизм на каждом уровне
1.  **Level 1: Orchestrator**
    *   `PlayerAssembler` и `MonsterAssembler` работают параллельно.
2.  **Level 2: Assembler**
    *   Все запросы к БД (attributes, inventory, skills) идут параллельно через `asyncio.gather`.
3.  **Level 3: Redis**
    *   Сохранение всех контекстов в Redis через Pipeline (один RTT).

**Результат:** Вместо 15+ последовательных операций получаем 3 параллельных этапа.

### Conditional Loading
Если `scope=status`, мы **НЕ загружаем** inventory и skills. Это экономит:
*   2 запроса к БД
*   ~60% данных
*   ~40% времени обработки

### Batch Operations
Всегда используем `WHERE IN` вместо циклов:
```python
# ✅ Правильно (1 запрос)
SELECT * FROM characters WHERE id IN (101, 102, 103)

# ❌ Неправильно (3 запроса)
for char_id in [101, 102, 103]:
    SELECT * FROM characters WHERE id = char_id
```

---

## Error Handling (Обработка ошибок)

### Level 1: Orchestrator
Если один Assembler упал, остальные продолжают работу.
```python
results = await asyncio.gather(*tasks, return_exceptions=True)

for entity_type, result in zip(task_mapping, results):
    if isinstance(result, Exception):
        log.error(f"Assembler {entity_type} failed: {result}")
        response.errors[entity_type] = ["assembler_error"]
    else:
        success_map, errors = result
        setattr(response, entity_type, success_map)
        response.errors[entity_type] = errors
```

### Level 2: Assembler
Если один ID не обработался, остальные продолжают.
```python
for char_id in ids:
    try:
        context = assemble_context(char_id, raw_data)
        contexts[char_id] = context
    except Exception as e:
        log.error(f"Failed for {char_id}: {e}")
        error_list.append(char_id)
        continue  # Не ломаем цикл
```

### Level 3: Redis
Если Redis недоступен, вся операция падает (это критическая ошибка).
```python
try:
    await redis.json().set(key, "$", data)
except RedisError as e:
    log.critical(f"Redis write failed: {e}")
    raise  # Прокидываем наверх
```

---

## Timing Breakdown (Пример для scope=combats, 10 игроков)
```
Step 0: Request Formation          ~0ms   (синхронный код)
Step 1: Routing                    ~0ms   (поиск модуля)
Step 2: Orchestrator Setup         ~1ms   (создание задач)
Step 3: Player Assembler
    3.1: Query Plan Build          ~0ms
    3.2: DB Queries (parallel)     ~50ms  (5 запросов одновременно)
    3.3: Data Assembly             ~5ms   (Python-код)
    3.4: Format (skip)             ~0ms
    3.5: DTO Assembly              ~15ms  (Pydantic + computed fields)
    3.6: Redis Save (pipeline)     ~10ms  (1 RTT для всех)
Step 4: Monster Assembler          ~30ms  (параллельно с Step 3)
Step 5: Response Assembly          ~1ms
Step 6: Return                     ~0ms

Total: ~80ms
```

**Для сравнения, v1 (всегда загружает всё):**
```
DB Queries (sequential): ~150ms
Total: ~200ms
```
**Выигрыш:** 2.5x faster для `scope=combats`, ещё быстрее для `scope=status`.

---

## Data Lifecycle (Жизненный цикл данных)
1.  **Создание:** Context Assembler создаёт данные в Redis по запросу.
2.  **Использование:** Заказчик (Combat/Status/etc) читает данные по UUID-ключу.
3.  **Обновление:** Данные в `temp:setup:{uuid}` иммутабельны. Если нужно обновление, делается новый запрос → новый UUID.
4.  **Удаление:** TTL = 1 час. Redis автоматически удалит ключ через час. Если нужно удалить раньше, заказчик может вызвать `DEL` вручную (но это не обязательно).

---

## Итог
**Data Flow в Context Assembler v2** — это хорошо структурированный конвейер с чёткими этапами и ответственностью каждого компонента.
*   **Orchestrator** координирует.
*   **Assemblers** загружают.
*   **Query Plan** определяет.
*   **Temp DTO** форматирует.
*   **Redis** хранит.

Параллелизм на каждом уровне. Условная загрузка через Scope. Batch операции везде.
**Результат: быстро, гибко, масштабируемо.**
