# Temp Context Hierarchy

⬅️ [Назад к Specs](../README.md) | 🏠 [Назад к Context Assembler v2](../../README.md)

Детальное описание иерархии Temp Context DTO, computed fields и принципов проектирования проекций.

---

## Философия иерархии

### Проблема монолитного DTO
В v1 был один `TempContextSchema` со всеми computed fields:
```
TempContextSchema:
- math_model (для боя)
- loadout (для боя)
- vitals (для боя)
- stats_display (для UI)
- inventory_groups (для UI)
- wallet_balance (для UI)
```
**Проблемы:**
1.  Все computed fields вызываются всегда, даже если не нужны
2.  Нельзя добавить новую проекцию без риска сломать существующие
3.  Логика разных модулей смешана в одном классе

### Решение: иерархия с наследованием
```
BaseTempContext (общее)
    ↓
CombatTempContext (боевое)
StatusTempContext (UI статуса)
InventoryTempContext (UI инвентаря)
ExplorationTempContext (проверки)
```
**Принципы:**
1.  Каждый контекст знает только о своих проекциях
2.  Базовый класс хранит сырые данные (core поля)
3.  Наследники добавляют computed fields для своих задач
4.  Один scope = один Temp Context класс

---

## BaseTempContext: Фундамент

### Назначение
Базовый класс, содержащий:
1.  Сырые данные из БД (core поля)
2.  Минимальные computed fields (meta)

Это "источник правды" — все остальные контексты строятся на его основе.

### Структура
```python
class BaseTempContext(BaseModel):
    # === CORE DATA (Internal Only) ===
    # Эти поля используются ТОЛЬКО для генерации проекций.
    # НЕ сохраняются в Redis (exclude при model_dump).
    
    core_attributes: CharacterAttributesReadDTO | None = None
    core_inventory: list[InventoryItemDTO] | None = None
    core_skills: list[SkillProgressDTO] | None = None
    core_vitals: dict[str, Any] | None = None
    core_meta: CharacterReadDTO | None = None
    core_symbiote: dict[str, Any] | None = None
    core_wallet: dict[str, Any] | None = None
    
    # === COMPUTED FIELDS (Redis Output) ===
    # Эти поля сохраняются в Redis как финальный результат.
    # Потребители получают ТОЛЬКО их.
    
    @computed_field(alias="meta")
    def meta_view(self) -> dict[str, Any]:
        """Базовая мета-информация, присутствует у всех контекстов."""
        if not self.core_meta:
            return {"entity_id": 0, "type": "unknown", "timestamp": 0}
        
        return {
            "entity_id": self.core_meta.character_id,
            "type": "player",
            "name": self.core_meta.name,
            "timestamp": int(time.time())
        }
```

### Правила работы с core полями

**1. Все core поля опциональны**
Если scope не требует какие-то данные, они остаются `None`.

**2. Computed fields должны обрабатывать None**
Каждый computed_field метод проверяет наличие данных.

**3. Exclude None при сохранении**
При сохранении в Redis используем `exclude_none`:
```python
context_data = context_schema.model_dump(
    by_alias=True,
    exclude_none=True  # Поля с None не попадут в Redis
)
```

---

## CombatTempContext: Боевой контекст

### Назначение
Предоставляет проекции данных для Combat System (RBC v3).

### Input Data (for generation)
*   `core_attributes`
*   `core_inventory` (equipped items)
*   `core_skills`
*   `core_vitals`
*   `core_symbiote`

*Used by @computed_field methods, not saved to Redis.*

### Output Projections (saved to Redis)

**1. math_model (v:raw структура)**
*   **Назначение:** Математическая модель для боевого калькулятора
*   **Формат:**
```json
{
    "attributes": {
        "strength": {"base": "15.0", "flats": {}, "percents": {}}
    },
    "modifiers": {
        "physical_damage_min": {"sources": {"item:123": "+25"}}
    },
    "tags": ["player"]
}
```

**2. loadout (арсенал)**
*   **Назначение:** Пояс, абилки, layout оружия
*   **Формат:**
```json
{
    "belt": [{"slot": "quick_slot_1", "item_id": 456, "type": "potion"}],
    "abilities": ["strike", "heavy_blow"],
    "equipment_layout": {"main_hand": "swords"}
}
```

**3. vitals (ресурсы)**
*   **Назначение:** HP и Energy для старта боя
*   **Формат:**
```json
{
    "hp_current": 100,
    "energy_current": 100
}
```

---

## StatusTempContext: UI статуса

### Назначение
Предоставляет проекции данных для экрана персонажа (Status Screen).

### Input Data (for generation)
*   `core_attributes`
*   `core_vitals`
*   `core_symbiote`

*Used by @computed_field methods, not saved to Redis.*

### Output Projections (saved to Redis)

**1. stats_display (статы для UI)**
*   **Назначение:** Форматированные статы для отображения
*   **Формат:**
```json
{
    "strength": {"value": 15, "label": "Сила"},
    "agility": {"value": 12, "label": "Ловкость"}
}
```

**2. vitals_display (ресурсы с процентами)**
*   **Назначение:** HP/Energy бары для UI
*   **Формат:**
```json
{
    "hp": {"current": 80, "max": 150, "percent": 53},
    "energy": {"current": 50, "max": 100, "percent": 50}
}
```

**3. symbiote_info (симбиот)**
*   **Назначение:** Информация о симбиоте для UI
*   **Формат:**
```json
{
    "name": "Тень",
    "gift": "pyromancy",
    "rank": 5
}
```

---

## InventoryTempContext: UI инвентаря

### Назначение
Предоставляет проекции данных для UI инвентаря и торговли.

### Input Data (for generation)
*   `core_inventory` (all items)
*   `core_wallet`

*Used by @computed_field methods, not saved to Redis.*

### Output Projections (saved to Redis)

**1. items_by_slot (группировка по слотам)**
*   **Назначение:** Инвентарь, сгруппированный по слотам экипировки
*   **Формат:**
```json
{
    "head_armor": {"item_id": 123, "name": "Шлем", "type": "armor"}
}
```

**2. items_by_type (группировка по типам)**
*   **Назначение:** Предметы, сгруппированные по категориям
*   **Формат:**
```json
{
    "weapon": [{"item_id": 456, "name": "Меч"}],
    "consumable": []
}
```

**3. wallet_display (кошелёк)**
*   **Назначение:** Отображение валюты и ресурсов
*   **Формат:**
```json
{
    "currency": {"dust": 100},
    "resources": {"iron": 50}
}
```

---

## MonsterTempContextSchema: Совместимость с боем

### Назначение
Контекст для монстров, совместимый по структуре с `CombatTempContext`.

### Особенность
У монстров нет разделения на множество таблиц (attributes, inventory, skills). Все данные лежат в JSON-полях одной таблицы.
Но для Combat System нужна та же структура computed fields (`math_model`, `loadout`, `vitals`).

### Структура
```python
class MonsterTempContextSchema(BaseModel):
    # НЕ наследует BaseTempContext (свои core поля)
    
    core_stats: dict[str, Any]       # scaled_base_stats из БД
    core_loadout: dict[str, Any]     # loadout_ids
    core_skills: list | dict         # skills_snapshot
    core_meta: dict[str, Any]        # {id, name, role, threat}
    
    # Те же computed fields, что у CombatTempContext
    @computed_field(alias="math_model")
    def combat_view(self) -> dict[str, Any]: ...
    
    @computed_field(alias="loadout")
    def loadout_view(self) -> dict[str, Any]: ...
    
    @computed_field(alias="vitals")
    def vitals_view(self) -> dict[str, Any]: ...
```

---

## Принципы проектирования Temp Context

### 1. Один контекст = один use case
Не создавай универсальные контексты "на все случаи жизни".
*   `CombatTempContext` только для боя.
*   `StatusTempContext` только для UI статуса.

### 2. Computed fields = проекции
Computed field не должен изменять core данные. Только читать и форматировать.
Это чистые функции: одинаковые core данные → одинаковый computed field.

### 3. Обрабатывай None
Каждый computed field проверяет наличие core данных.
Если данных нет, возвращай дефолт или пустую структуру.

### 4. Используй alias
Computed fields всегда используют alias для читаемости в Redis:
```python
@computed_field(alias="stats_display")  # В Redis будет "stats_display"
def stats_view(self): ...               # В Python это stats_view
```

### 5. Держи логику простой
Computed field не должен делать сложные вычисления.
Если нужна сложная логика, вынеси её в helper-функцию.

---

## Итог
**Иерархия Temp Context** — это способ организации проекций данных для разных потребителей.
*   Базовый класс хранит сырые данные.
*   Наследники добавляют проекции через computed fields.
*   Каждый контекст знает только о своих задачах.

Это делает систему гибкой, расширяемой и понятной.
