# Data Transfer Objects (DTOs)

⬅️ [Назад к Specs](../README.md) | 🏠 [Назад к Context Assembler v2](../../README.md)

Полная спецификация всех DTO, используемых в Context Assembler v2.

---

## 1. Input DTOs (Request Layer)

### `ContextRequestDTO`
*   **Назначение:** Основной запрос к Context Assembler
*   **Файл:** `apps/game_core/system/context_assembler/dtos.py`

**Поля:**
```python
class ContextRequestDTO(BaseModel):
    player_ids: list[int] = Field(default_factory=list)
    monster_ids: list[str] = Field(default_factory=list)  # UUID as strings
    pet_ids: list[int] = Field(default_factory=list)
    
    scope: Literal["combats", "status", "inventory", "exploration", "trade", "tutorial"]
```

**Описание полей:**
*   `player_ids` — Список ID персонажей игроков для загрузки
*   `monster_ids` — Список UUID монстров (строки, не int)
*   `pet_ids` — Список ID петов (будущее расширение)
*   `scope` — Флаг, определяющий цель использования данных

**Валидация:**
1.  Хотя бы один из списков (`player_ids`, `monster_ids`, `pet_ids`) должен быть не пустым
2.  `scope` должен быть из допустимых значений
3.  `monster_ids` должны быть валидными UUID-строками

**Примеры использования:**
```python
# Запрос для боя
request = ContextRequestDTO(
    player_ids=[101, 102],
    monster_ids=["550e8400-e29b-41d4-a716-446655440000"],
    scope="combats"
)

# Запрос для статуса одного игрока
request = ContextRequestDTO(
    player_ids=[101],
    scope="status"
)

# Запрос для инвентаря
request = ContextRequestDTO(
    player_ids=[101],
    scope="inventory"
)
```

---

## 2. Output DTOs (Response Layer)

### `ContextResponseDTO`
*   **Назначение:** Результат сборки контекста
*   **Файл:** `apps/game_core/system/context_assembler/dtos.py`

**Поля:**
```python
class ContextResponseDTO(BaseModel):
    player: dict[int, str] = Field(default_factory=dict)
    monster: dict[str, str] = Field(default_factory=dict)
    pet: dict[int, str] = Field(default_factory=dict)
    
    errors: dict[str, list[str | int]] = Field(
        default_factory=lambda: {"player": [], "monster": [], "pet": []}
    )
```

**Описание полей:**
*   `player` — Маппинг `{char_id: redis_key}` для успешно обработанных игроков
*   `monster` — Маппинг `{monster_uuid: redis_key}` для монстров
*   `pet` — Маппинг `{pet_id: redis_key}` для петов
*   `errors` — Списки ID сущностей, которые не удалось обработать

**Формат Redis ключей:**
Все значения в player/monster/pet имеют формат: `temp:setup:{uuid4}`
Пример: `temp:setup:a1b2c3d4-e5f6-7890-abcd-ef1234567890`

**Важно:**
*   Redis keys содержат **ТОЛЬКО** отформатированные проекции (computed fields).
*   `core_*` поля (сырые данные) **не доступны** потребителям через эти ключи.

**Примеры ответов:**
```python
# Успешный ответ
response = ContextResponseDTO(
    player={
        101: "temp:setup:uuid-1",
        102: "temp:setup:uuid-2"
    },
    monster={
        "550e8400-e29b-41d4-a716-446655440000": "temp:setup:uuid-3"
    },
    errors={"player": [], "monster": [], "pet": []}
)

# Ответ с ошибками
response = ContextResponseDTO(
    player={
        101: "temp:setup:uuid-1"
        # 102 не обработан
    },
    monster={},
    errors={
        "player": [102],  # Не найден в БД
        "monster": ["invalid-uuid"],  # Невалидный UUID
        "pet": []
    }
)
```

**Обработка ошибок:**
Если ID присутствует в `errors`, значит:
1.  Сущность не найдена в БД
2.  Произошла ошибка при трансформации данных
3.  Произошла ошибка при сохранении в Redis

Заказчик должен проверять `errors` и обрабатывать отсутствующие ID.

---

## 3. Internal DTOs (Processing Layer)
*Эти DTO используются внутри системы и не возвращаются наружу.*

### `QueryPlanDTO` (планируется)
*   **Назначение:** Описание плана запросов для конкретного scope

**Структура:**
```python
class QueryPlanDTO(BaseModel):
    scope: str
    tables: list[str]  # ["attributes", "inventory", "skills"]
    filters: dict[str, Any]  # {"inventory": {"location": "equipped"}}
    temp_dto_class: str  # "CombatTempContext"
```

**Пример:**
```python
plan = QueryPlanDTO(
    scope="combats",
    tables=["attributes", "inventory", "skills", "vitals", "symbiote"],
    filters={"inventory": {"location": "equipped"}},
    temp_dto_class="CombatTempContext"
)
```

### `AssemblerResultDTO` (внутренний)
*   **Назначение:** Результат работы одного Assembler

**Структура:**
```python
# Tuple[success_map, error_list]
success_map: dict[int | str, str]  # {entity_id: redis_key}
error_list: list[int | str]  # [failed_entity_ids]
```

**Используется в:**
```python
async def process_batch(
    ids: list[Any], 
    scope: str
) -> tuple[dict[Any, str], list[Any]]:
    ...
    return success_map, error_list
```

---

## 4. Temp Context DTOs (Redis Storage Layer)
*Эти DTO определяют структуру данных, сохраняемых в Redis.*

### `BaseTempContext`
*   **Назначение:** Базовый класс для всех Temp Context
*   **Файл:** `apps/game_core/system/context_assembler/schemas/temp_context.py`

**Поля (core data):**
```python
class BaseTempContext(BaseModel):
    # Источники правды (сырые данные из БД)
    core_attributes: CharacterAttributesReadDTO | None = None
    core_inventory: list[InventoryItemDTO] | None = None
    core_skills: list[SkillProgressDTO] | None = None
    core_vitals: dict[str, Any] | None = None
    core_meta: CharacterReadDTO | None = None
    core_symbiote: dict[str, Any] | None = None
    core_wallet: dict[str, Any] | None = None
```

**Computed Fields (базовые):**
```python
@computed_field(alias="meta")
def meta_view(self) -> dict[str, Any]:
    # Всегда присутствует у всех контекстов
    return {
        "entity_id": self.core_meta.character_id,
        "type": "player",
        "timestamp": int(time.time())
    }
```

**Принципы:**
1.  Все `core` поля опциональны (`None` если не загружены)
2.  При сохранении в Redis поля с `None` не включаются (`exclude_none=True`)
3.  Computed fields вызываются автоматически при `model_dump(by_alias=True)`

---

### `CombatTempContext`
*   **Назначение:** Контекст для боевой системы
*   **Файл:** `apps/game_core/system/context_assembler/schemas/temp_context.py`
*   **Наследует:** `BaseTempContext`

**Дополнительные Computed Fields:**
```python
@computed_field(alias="math_model")
def combat_view(self) -> dict[str, Any]:
    # Структура v:raw для Combat System
    return {
        "attributes": {...},  # Base stats с модификаторами
        "modifiers": {...},   # Secondary stats от экипировки
        "tags": [...]         # Теги для логики боя
    }

@computed_field(alias="loadout")
def loadout_view(self) -> dict[str, Any]:
    # Арсенал персонажа
    return {
        "belt": [...],          # Quick slots
        "abilities": [...],     # Доступные абилки
        "equipment_layout": {}  # main_hand, off_hand, etc
    }

@computed_field(alias="vitals")
def vitals_view(self) -> dict[str, Any]:
    # HP и Energy
    return {
        "hp_current": 100,
        "energy_current": 50
    }
```

**Используется в:**
*   Combat System (RBC v3)
*   Shadow Duel
*   Arena Matches

**Требуемые core поля:**
*   `core_attributes` (обязательно)
*   `core_inventory` (equipped items)
*   `core_skills`
*   `core_vitals`
*   `core_symbiote`

---

### `StatusTempContext`
*   **Назначение:** Контекст для экрана персонажа
*   **Файл:** `apps/game_core/system/context_assembler/schemas/status_context.py`
*   **Наследует:** `BaseTempContext`

**Дополнительные Computed Fields:**
```python
@computed_field(alias="stats_display")
def stats_view(self) -> dict[str, Any]:
    # Форматированные статы для UI
    return {
        "strength": {"value": 15, "label": "Сила"},
        "agility": {"value": 12, "label": "Ловкость"},
        # ... остальные статы
    }

@computed_field(alias="vitals_display")
def vitals_view(self) -> dict[str, Any]:
    # HP/Energy для UI
    return {
        "hp": {"current": 100, "max": 150, "percent": 66},
        "energy": {"current": 50, "max": 100, "percent": 50}
    }

@computed_field(alias="symbiote_info")
def symbiote_view(self) -> dict[str, Any]:
    # Информация о симбиоте
    return {
        "name": "Тень",
        "gift": "pyromancy",
        "rank": 5
    }
```

**Используется в:**
*   StatusService
*   Character Menu Handler
*   Profile Screen

**Требуемые core поля:**
*   `core_attributes` (обязательно)
*   `core_vitals` (обязательно)
*   `core_symbiote`

---

### `InventoryTempContext`
*   **Назначение:** Контекст для UI инвентаря
*   **Файл:** `apps/game_core/system/context_assembler/schemas/inventory_context.py`
*   **Наследует:** `BaseTempContext`

**Дополнительные Computed Fields:**
```python
@computed_field(alias="items_by_slot")
def inventory_view(self) -> dict[str, Any]:
    # Группировка по слотам
    return {
        "head_armor": {...},
        "main_hand": {...},
        "ring_1": {...},
        # ...
    }

@computed_field(alias="items_by_type")
def type_groups(self) -> dict[str, list]:
    # Группировка по типам
    return {
        "weapon": [...],
        "armor": [...],
        "consumable": [...]
    }

@computed_field(alias="wallet_display")
def wallet_view(self) -> dict[str, Any]:
    # Кошелёк
    return {
        "currency": {"dust": 100, "shards": 5},
        "resources": {"iron_ore": 50},
        "components": {"iron_ingot": 10}
    }
```

**Используется в:**
*   InventoryService
*   TradeService
*   CraftingService

**Требуемые core поля:**
*   `core_inventory` (all items)
*   `core_wallet`

---

### `MonsterTempContextSchema`
*   **Назначение:** Контекст для монстров (совместим с `CombatTempContext`)
*   **Файл:** `apps/game_core/system/context_assembler/schemas/monster_temp_context.py`

**Особенности:**
Монстры используют ту же структуру computed fields, что и игроки (`math_model`, `loadout`, `vitals`), чтобы Combat System не видел разницы.

**Поля:**
```python
class MonsterTempContextSchema(BaseModel):
    core_stats: dict[str, Any]      # scaled_base_stats из БД
    core_loadout: dict[str, Any]    # loadout_ids
    core_skills: list | dict        # skills_snapshot
    core_meta: dict[str, Any]       # {id, name, role, threat}
```

**Computed Fields:**
Идентичны `CombatTempContext`:
*   `math_model` (v:raw структура)
*   `loadout` (abilities)
*   `vitals` (HP/Energy, обычно -1 для автокалькуляции)
*   `meta` (entity_id, type="monster")

---

## 5. Redis Storage Format

### Ключи
*   **Формат:** `temp:setup:{uuid4}`
*   **Пример:** `temp:setup:a1b2c3d4-e5f6-7890-abcd-ef1234567890`

### Структура данных
```python
{
    "math_model": {...},      # Computed field 1
    "loadout": {...},         # Computed field 2
    "vitals": {...},          # Computed field 3
    "meta": {...},            # Computed field 4 (всегда есть)
    
    # Core data НЕ сохраняется (только computed fields)
}
```

### TTL
*   **По умолчанию:** 3600 секунд (1 час)
*   **Можно настроить** через конфигурацию.

### Команда сохранения
```python
await redis.json().set(key, "$", context_data)
await redis.expire(key, 3600)
```

---

## 6. Validation Rules

### `ContextRequestDTO`
1.  Минимум один список ID должен быть не пустым
2.  `scope` должен быть валидным значением из Enum
3.  `monster_ids` должны быть строками (UUID)

### `ContextResponseDTO`
1.  Все `redis_key` должны соответствовать паттерну `temp:setup:{uuid}`
2.  `errors` должны содержать только ID, которых нет в success mappings

### `Temp Context`
1.  `core` поля могут быть `None` (если не загружены через scope)
2.  `computed_field` методы должны обрабатывать `None` в core полях
3.  `model_dump(by_alias=True)` всегда использовать для сохранения в Redis

---

## 7. Type Hints
Все DTO используют строгую типизацию:
*   Pydantic v2 `BaseModel`
*   Type hints для всех полей
*   Field validators где нужно
*   Computed field decorators для проекций

Mypy должен проходить без ошибок на всех DTO.

---

## 8. Future DTOs (планируется)
*   **ExplorationTempContext** — Для проверок в мире (скилл-чеки, препятствия)
*   **TradeTempContext** — Для торговли и оценки предметов
*   **TutorialTempContext** — Упрощённый контекст для обучения

---

## Итог
Все DTO в Context Assembler v2 имеют чёткое назначение и строгую типизацию.
*   **Request/Response DTOs** определяют контракт API.
*   **Temp Context DTOs** определяют структуру хранения в Redis.
*   **Computed fields** обеспечивают гибкость проекций для разных потребителей.
