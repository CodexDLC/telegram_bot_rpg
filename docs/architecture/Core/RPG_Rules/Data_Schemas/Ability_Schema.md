# 💾 Schema: Abilities (Способности)

[⬅️ Назад: Data Schemas](./README.md) | [📖 Правила: Skills](../Skills/README.md)

---

## 📋 Обзор
Техническая реализация активных способностей.
Делятся на **Gift Abilities** (магия) и **Combat Maneuvers** (физика).

## ⚙️ DTO Structure

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Any

class AbilityType(str, Enum):
    INSTANT = "instant"       # Мгновенное действие (не завершает ход)
    REACTION = "reaction"     # Ответное действие (в фазе защиты)
    PASSIVE = "passive"       # Пассивный эффект

class AbilitySource(str, Enum):
    GIFT = "gift"             # Дар (Energy + Gift Token)
    COMBAT = "combat"         # Боевой (Combat Tokens)

class AbilityTarget(str, Enum):
    SELF = "self"
    SINGLE_ENEMY = "single_enemy"
    ALL_ENEMIES = "all_enemies"
    SINGLE_ALLY = "single_ally"
    ALL_ALLIES = "all_allies"

class EffectConfig(BaseModel):
    trigger: str              # "on_hit", "on_use", "on_cast"
    action: str               # "apply_status", "heal", "buff", "deal_damage"
    params: dict[str, Any]    # Параметры эффекта

class AbilityDTO(BaseModel):
    ability_id: str           # Уникальный ID
    name_en: str
    name_ru: str
    
    type: AbilityType
    source: AbilitySource
    target: AbilityTarget
    
    # Стоимость ресурсов
    cost_energy: int = 0      # Энергия (для Gift)
    cost_hp: int = 0          # HP (для магии крови)
    
    # Стоимость токенов (Главный ограничитель)
    # Keys: "gift", "hit", "block", "dodge", "counter", "tempo"
    cost_tokens: dict[str, int] = Field(default_factory=dict)
    
    # Механика
    flags: dict[str, Any] = Field(default_factory=dict)
    effects: list[EffectConfig] = Field(default_factory=list)
    
    description: str
```

## 📝 Пример: Fireball
```python
fireball_config = {
    "ability_id": "fireball",
    "name_en": "Fireball",
    "name_ru": "Огненный шар",
    "type": "instant",
    "source": "gift",
    "target": "all_enemies",
    "cost_energy": 25,
    "cost_tokens": {"gift": 1},
    "flags": {"damage": {"fire": True}, "formula": {"ignore_block": True}},
    "effects": [
        {
            "trigger": "on_hit",
            "action": "apply_status",
            "params": {"status_id": "burn", "duration": 3}
        }
    ],
    "description": "Магическая атака огнем. Тратит заряд Дара."
}
```
