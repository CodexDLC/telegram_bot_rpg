# 💾 Schema: Effects (Эффекты)

[⬅️ Назад: Data Schemas](./README.md) | [📖 Правила: Skills](../Skills/README.md)

---

## 📋 Обзор
Техническая реализация статусных эффектов (DoT, HoT, Buff, Debuff, Control).
Поддерживает **Dynamic Scaling** (сила эффекта зависит от урона).

## ⚙️ DTO Structure

```python
from pydantic import BaseModel
from enum import Enum
from typing import Any

class EffectType(str, Enum):
    DOT = "dot"
    HOT = "hot"
    BUFF = "buff"
    DEBUFF = "debuff"
    CONTROL = "control"

class EffectDTO(BaseModel):
    effect_id: str              # Уникальный ID (например, "bleed")
    name_en: str
    name_ru: str
    
    type: EffectType            # Тип эффекта
    duration: int               # Длительность в разменах (Exchange)
    
    # --- Impact Configuration ---
    # Фиксированное значение (Legacy/Simple)
    impact_flat: dict[str, int] = {} 
    
    # Динамическое масштабирование
    # Если указано, impact рассчитывается в момент наложения
    scaling: dict[str, Any] = {}
    # Пример: {"source": "snapshot_damage", "stat": "hp", "power": 1}
    
    # Модификаторы характеристик (для Buff/Debuff)
    modifiers: dict[str, Any] = {}
    
    # Флаги состояния (для Control)
    flags: dict[str, Any] = {}
    
    description: str
```

## 📝 Пример: Bleed (Dynamic)
```python
bleed_config = {
    "effect_id": "bleed",
    "name_en": "Bleeding",
    "name_ru": "Кровотечение",
    "type": "dot",
    "duration": 3,
    "scaling": {
        "source": "snapshot_damage",
        "stat": "hp",
        "power": 2  # 20% от нанесенного урона каждый ход
    },
    "description": "Глубокая рана кровоточит, нанося урон, зависящий от силы удара."
}
```
