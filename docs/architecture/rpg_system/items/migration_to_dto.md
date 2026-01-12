# Migration: Items to Pydantic DTO

## 🎯 Цель
Перевести библиотеку предметов (`apps/game_core/resources/game_data/items`) с устаревших `TypedDict` на строгие `Pydantic DTO`. Это обеспечит валидацию данных при старте и унифицирует архитектуру с `skills` и `abilities`.

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
    narrative_tags: list[str]
```

### 3. BaseItemDTO
```python
class BaseItemDTO(BaseModel):
    id: str
    name_ru: str
    slot: str
    type: str  # weapon, armor, accessory
    
    # Характеристики
    base_power: int
    base_durability: int
    damage_spread: float = 0.1
    
    # Крафт
    allowed_materials: list[str]  # ["ingots", "leathers"]
    
    # Бонусы
    implicit_bonuses: dict[str, float] = Field(default_factory=dict)
    
    # Триггеры (ссылки на TriggerRegistry)
    triggers: list[str] = Field(default_factory=dict)
    
    narrative_tags: list[str] = Field(default_factory=list)
```

## 📝 План работ

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
