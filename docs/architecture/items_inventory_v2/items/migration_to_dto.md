# Migration: Items to Pydantic DTO

## 🎯 Цель
Перевести библиотеку предметов (`apps/game_core/resources/game_data/items`) с устаревших `TypedDict` на строгие `Pydantic DTO`. Это обеспечит валидацию данных при старте и унифицирует архитектуру с `skills` и `abilities`.

---

## ✅ Статус миграции

| Компонент              | Статус     | Примечания                              |
|------------------------|------------|-----------------------------------------|
| ResourceDTO            | ✅ Готово  | Используется для сырья и валюты         |
| MaterialDTO            | ✅ Готово  | Используется для материалов             |
| BaseItemDTO            | ⚠️ Частично| Требует обновления под RBC v3.1         |
| ItemCoreData           | ✅ Готово  | Базовый класс для всех предметов        |
| WeaponData             | ✅ Готово  | Новая схема (power, spread, triggers)   |
| ArmorData              | ✅ Готово  | Новая схема (power)                     |
| AccessoryData          | ✅ Готово  |                                         |
| ConsumableData         | ✅ Готово  |                                         |
| InventoryItemDTO       | ✅ Готово  | Полиморфный wrapper                     |

---

## 🛠️ Новые схемы (Schemas)

### 1. ResourceDTO
```python
class ResourceDTO(BaseModel):
    id: str
    name_ru: str
    base_price: int
    narrative_description: str
```

### 2. MaterialDTO
```python
class MaterialDTO(BaseModel):
    id: str
    name_ru: str
    tier_mult: float
    slots: int
    narrative_tags: list[str] = Field(default_factory=list)
```

### 3. BaseItemDTO
```python
class BaseItemDTO(BaseModel):
    id: str
    name_ru: str
    slot: str
    type: str | None = None  # weapon, armor, accessory
    
    # Характеристики
    base_power: int
    base_durability: int
    damage_spread: float = 0.1
    
    # Типы урона/защиты
    damage_type: str | None = None
    defense_type: str | None = None
    
    # Крафт
    allowed_materials: list[str] = Field(default_factory=list)
    extra_slots: list[str] = Field(default_factory=list)
    
    # Бонусы
    implicit_bonuses: dict[str, float] = Field(default_factory=dict)
    
    # Триггеры (ссылки на TriggerRegistry)
    triggers: list[str] = Field(default_factory=list)
    
    narrative_tags: list[str] = Field(default_factory=list)
```

**⚠️ Исправлена ошибка:** `triggers: list[str] = Field(default_factory=list)` (было `default_factory=dict`)

---

## 📝 План работ (Оригинальный)

1.  **Создать `schemas.py`:**
    *   В `apps/game_core/resources/game_data/items/schemas.py`.
    *   Определить все DTO.

2.  **Миграция файлов данных:**
    *   Пройтись по всем файлам в `raw_resource/`, `material/`, `base_item/`.
    *   Заменить словари на вызовы конструкторов.
    *   *Пример:*
        ```python
        # Было
        "res_iron": {"name_ru": "Железо", ...}
        
        # Станет
        "res_iron": ResourceDTO(name_ru="Железо", ...)
        ```

3.  **Обновить Реестры (`__init__.py`):**
    *   Обновить `bases.py`, `materials.py`, `raw_resources.py`, чтобы они типизировались как `dict[str, DTO]`.

4.  **Валидация:**
    *   Запустить проект. Pydantic автоматически проверит все данные и упадет, если где-то ошибка (например, `tier_mult` строка вместо float).

---

## 🔄 Post-Migration Updates (RBC v3.1)

После завершения базовой миграции на Pydantic DTO, потребовались дополнительные обновления для интеграции с новой боевой системой (RBC v3.1).

### 🎯 Проблемы старой схемы

**1. Устаревшие поля оружия:**
```python
# Старая схема (Legacy)
data_payload = {
    "damage_min": 12,  # ❌
    "damage_max": 18,  # ❌
}

# Новая схема (RBC v3.1)
data_payload = {
    "power": 15.0,     # ✅ Базовая сила
    "spread": 0.2,     # ✅ Разброс (±20%)
}
```

**2. Устаревшие поля брони:**
```python
# Старая схема
data_payload = {
    "protection": 10  # ❌ Неясное название
}

# Новая схема
data_payload = {
    "power": 10.0     # ✅ Flat Damage Reduction
}
```

**3. Триггеры не у всех предметов:**
```python
# Проблема: BaseItemDTO.triggers для ВСЕХ предметов
BaseItemDTO(triggers=["trigger_bleed"])  # ❌ Броня тоже имеет триггеры?

# Решение: Триггеры только у WeaponData
WeaponData(triggers=["trigger_bleed"])   # ✅
ArmorData(triggers=[])                   # ✅ Всегда пусто
```

---

### 🆕 Новые DTO схемы (RBC v3.1)

#### ItemCoreData (Базовый класс)
```python
class ItemCoreData(BaseModel):
    name: str
    description: str
    base_price: int
    
    components: ItemComponents | None = None
    durability: ItemDurability | None = None
    
    narrative_tags: list[str] = Field(default_factory=list)
    
    implicit_bonuses: dict[str, float] = Field(default_factory=dict)
    bonuses: dict[str, float] = Field(default_factory=dict)
```

**Изменения:**
- ✅ Добавлено `components` (ItemComponents) — для хранения base_id, material_id, essence_id
- ✅ Добавлено `durability` (ItemDurability) — для прочности

#### WeaponData (Оружие)
```python
class WeaponData(ItemCoreData):
    # Математика урона (НОВОЕ)
    power: float              # Базовая сила (заменяет damage_min/max)
    spread: float = 0.1       # Разброс (0.1 = ±10%)
    accuracy: float = 0.0     # Базовая точность
    
    # Механика боя
    crit_chance: float = 0.0
    parry_chance: float = 0.0
    evasion_penalty: float = 0.0
    
    # Триггеры (ТОЛЬКО У ОРУЖИЯ!)
    triggers: list[str] = Field(default_factory=list)
    
    # Классификация
    grip: str = "1h"          # "1h", "2h", "off_hand"
    subtype: str              # "sword", "axe", "bow"
    related_skill: str | None = None
    valid_slots: list[str]
```

**Ключевые изменения:**
- ✅ `power` вместо `damage_min/damage_max`
- ✅ `spread` для разброса урона
- ✅ `accuracy` для базовой точности
- ✅ `triggers` — только у оружия

#### ArmorData (Броня)
```python
class ArmorData(ItemCoreData):
    # Математика защиты (НОВОЕ)
    power: float              # Flat Damage Reduction (заменяет protection)
    
    # Механика защиты
    block_chance: float = 0.0
    evasion_penalty: float = 0.0
    dodge_cap_mod: float = 0.0
    
    # Триггеров НЕТ (защита через скиллы)
    triggers: list[str] = Field(default_factory=list)  # Всегда []
    
    # Классификация
    subtype: str              # "heavy", "light", "shield"
    related_skill: str | None = None
    valid_slots: list[str]
```

**Ключевые изменения:**
- ✅ `power` вместо `protection`
- ✅ `triggers` всегда пустой список

---

### 🔧 Необходимые изменения в коде

#### 1. ItemAssembler (требует рефакторинг)

**Файл:** `apps/game_core/modules/inventory/Item/item_assembler.py`

**Текущий код (строки 89-96):**
```python
if item_type == ItemType.WEAPON:
    spread = base_data.get("damage_spread", 0.2)
    dmg_min = int(final_power * (1 - spread))
    dmg_max = int(final_power * (1 + spread))
    data_payload["damage_min"] = max(1, dmg_min)  # ❌ Удалить
    data_payload["damage_max"] = max(2, dmg_max)  # ❌ Удалить
elif item_type == ItemType.ARMOR:
    data_payload["protection"] = max(1, final_power)  # ❌ Удалить
```

**Новый код (нужно реализовать):**
```python
if item_type == ItemType.WEAPON:
    data_payload["power"] = float(final_power)           # ✅
    data_payload["spread"] = base_data.get("damage_spread", 0.2)  # ✅
    data_payload["accuracy"] = base_data.get("base_accuracy", 0.0)  # ✅
    data_payload["crit_chance"] = base_data.get("crit_chance", 0.0)  # ✅
    data_payload["parry_chance"] = base_data.get("parry_chance", 0.0)  # ✅
    data_payload["evasion_penalty"] = base_data.get("evasion_penalty", 0.0)  # ✅
    data_payload["triggers"] = base_data.get("triggers", [])  # ✅
    data_payload["grip"] = base_data.get("grip", "1h")  # ✅
    data_payload["subtype"] = base_data.get("subtype", "unknown")  # ✅
    data_payload["related_skill"] = base_data.get("related_skill")  # ✅

elif item_type == ItemType.ARMOR:
    data_payload["power"] = float(final_power)  # ✅ (Flat reduction)
    data_payload["block_chance"] = base_data.get("block_chance", 0.0)  # ✅
    data_payload["evasion_penalty"] = base_data.get("evasion_penalty", 0.0)  # ✅
    data_payload["dodge_cap_mod"] = base_data.get("dodge_cap_mod", 0.0)  # ✅
    data_payload["triggers"] = []  # ✅ Всегда пусто
    data_payload["subtype"] = base_data.get("subtype", "unknown")  # ✅
    data_payload["related_skill"] = base_data.get("related_skill")  # ✅
```

#### 2. Триггеры от аффиксов

**Проблема:** Аффиксы не могут добавлять триггеры.

**Текущий код (_apply_bundles):**
```python
# Применяем только в bonuses
for effect_key in bundle["effects"]:
    effect = EFFECTS_DB.get(effect_key)
    final_value = effect["base_value"] * material_data["tier_mult"]
    target_field = effect["target_field"]
    data_payload["bonuses"][target_field] = final_value
```

**Решение (Option B — триггеры в bonuses):**
```python
# Если эффект — это триггер
if effect.get("is_trigger", False):
    data_payload["bonuses"][f"trigger_{effect['id']}"] = True
else:
    # Обычный стат
    final_value = effect["base_value"] * material_data["tier_mult"]
    data_payload["bonuses"][target_field] = final_value
```

**Пример:**
```python
# Аффикс "vampirism"
EFFECTS_DB["vampirism"] = {
    "id": "vampirism",
    "is_trigger": True,  # ✅ Это триггер
    "target_field": "trigger_vampirism"
}

# Результат
data_payload["bonuses"] = {
    "trigger_vampirism": True  # ✅
}
```

#### 3. BaseItemDTO — убрать лишние поля

**Проблема:** `BaseItemDTO.triggers` существует, но триггеры должны быть только у оружия.

**Вариант A (консервативный):** Оставить поле, но документировать
```python
class BaseItemDTO(BaseModel):
    triggers: list[str] = Field(default_factory=list)
    # NOTE: Используется только для weapon. Для armor/accessory всегда []
```

**Вариант B (радикальный):** Убрать из BaseItemDTO
```python
class BaseItemDTO(BaseModel):
    # triggers убрано!
    # Только WeaponData имеет triggers
```

**Рекомендация:** Вариант A (безопаснее для существующего кода).

---

### 📊 Сравнение схем

| Поле              | Legacy (TypedDict) | Current (DTO)     | RBC v3.1 (WeaponData) |
|-------------------|--------------------|-------------------|-----------------------|
| `damage_min`      | ✅ int             | ❌ Удалено        | ❌ Удалено            |
| `damage_max`      | ✅ int             | ❌ Удалено        | ❌ Удалено            |
| `protection`      | ✅ int             | ❌ Удалено        | ❌ Удалено            |
| `power`           | ❌ Нет             | ❌ Нет            | ✅ float              |
| `spread`          | ❌ Нет             | ❌ Нет            | ✅ float              |
| `accuracy`        | ❌ Нет             | ❌ Нет            | ✅ float              |
| `triggers`        | ❌ Нет             | ✅ list[str]      | ✅ list[str]          |
| `grip`            | ❌ Нет             | ❌ Нет            | ✅ str                |
| `subtype`         | ❌ Нет             | ❌ Нет            | ✅ str                |

---

## 🚀 План дальнейших работ

### Фаза 1: Рефакторинг ItemAssembler
- [ ] Обновить код под новые поля (`power`, `spread`, `triggers`)
- [ ] Убрать старые поля (`damage_min`, `damage_max`, `protection`)
- [ ] Добавить копирование триггеров из `BaseItemDTO`
- [ ] Тестирование создания предметов

### Фаза 2: Поддержка триггеров от аффиксов
- [ ] Обновить `_apply_bundles` для триггеров
- [ ] Добавить `is_trigger` флаг в `EFFECTS_DB`
- [ ] Документировать формат триггеров в bonuses

### Фаза 3: Валидация и тесты
- [ ] Добавить Pydantic validators для `power >= 0`
- [ ] Добавить validators для `spread` (0.0 - 1.0)
- [ ] Добавить Literal для `grip` ("1h", "2h", "off_hand")
- [ ] Написать unit-тесты для ItemAssembler

### Фаза 4: Документация
- [ ] Обновить примеры в документации
- [ ] Добавить migration guide для разработчиков
- [ ] Документировать новые поля в DTO reference

---

## 📚 Связанная документация

- **Система предметов:** [README.md](../../rpg_system/items/README.md)
- **DTO справочник:** [01_item_dto_reference.md](./01_item_dto_reference.md)
- **Конвейер создания:** [02_item_creation_pipeline.md](./02_item_creation_pipeline.md)
- **Триггеры:** [weapon_triggers/README.md](./weapon_triggers/README.md)
- **Боевая система:** `/docs/architecture/combat_system_v3/`

---

**Последнее обновление:** Январь 2026  
**Статус:** Миграция завершена, требуется рефакторинг ItemAssembler