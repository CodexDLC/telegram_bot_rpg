# Abilities (Активные способности)

## Философия

Активные способности — это действия, которые игрок использует для получения преимущества в бою. Они делятся на две фундаментальные категории в зависимости от используемого ресурса.

### 1. Gift Abilities (Способности Дара)
Магические или мутационные силы, дарованные Симбиотом/Даром.
- **Ресурс:** Требуют **Энергию** + **Gift Token** (Токен Дара)
- **Механика:** Gift Tokens накапливаются каждый раунд. Это ограничитель частоты использования сильных способностей ("кулдаун" через ресурс)
- **Примеры:** Fireball, Heal, Shadow Step

### 2. Combat Maneuvers (Боевые Маневры)
Приемы, основанные на физической подготовке и тактике.
- **Ресурс:** Требуют **Combat Tokens** (Боевые Токены)
- **Типы Токенов:**
  - `hit` (Точность/Удар)
  - `block` (Блок)
  - `dodge` (Уклонение)
  - `counter` (Контрудар)
  - `tempo` (Темп/Инициатива)
- **Примеры:** Perfect Block (тратит Block), Feint (тратит Tempo), Riposte (тратит Counter)

---

## Ключевые отличия от Exchange

**Instant Mechanics:**
Большинство способностей имеют тип `INSTANT`.
- **Не завершают ход:** Использование способности не передает ход противнику (в отличие от `Exchange`)
- **Chaining:** Можно использовать несколько способностей подряд, пока есть ресурсы (Токены/Энергия)

---

## Формат DTO
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

---

## Примеры

### Gift Ability: Fireball
```python
AbilityDTO(
    ability_id="fireball",
    name_en="Fireball",
    name_ru="Огненный шар",
    type=AbilityType.INSTANT,
    source=AbilitySource.GIFT,
    target=AbilityTarget.ALL_ENEMIES,
    
    cost_energy=25,
    cost_tokens={"gift": 1},  # Тратит 1 заряд Дара
    
    flags={"damage": {"fire": True}, "formula": {"ignore_block": True}},
    effects=[
        EffectConfig(
            trigger="on_hit",
            action="apply_status",
            params={"status_id": "burn", "duration": 3}
        )
    ],
    description="Магическая атака огнем. Тратит заряд Дара."
)
```

### Combat Maneuver: Shield Bash
```python
AbilityDTO(
    ability_id="shield_bash",
    name_en="Shield Bash",
    name_ru="Удар щитом",
    type=AbilityType.INSTANT,
    source=AbilitySource.COMBAT,
    target=AbilityTarget.SINGLE_ENEMY,
    
    cost_tokens={
        "block": 1,
        "tempo": 1
    },
    
    flags={"force": {"stun_check": True}},
    effects=[
        EffectConfig(
            trigger="on_hit",
            action="apply_status",
            params={"status_id": "stun", "duration": 1}
        )
    ],
    description="Использует инерцию блока для оглушающего удара."
)
```

### Gift Ability: Heal
```python
AbilityDTO(
    ability_id="heal",
    name_en="Heal",
    name_ru="Лечение",
    type=AbilityType.INSTANT,
    source=AbilitySource.GIFT,
    target=AbilityTarget.SELF,
    
    cost_energy=15,
    cost_tokens={"gift": 1},
    
    flags={},
    effects=[
        EffectConfig(
            trigger="on_cast",
            action="heal",
            params={"value": 30}
        )
    ],
    description="Восстанавливает HP за счет Дара."
)
```

---

## Интеграция

### Token Management

**Gift Tokens:**
- Генерируются автоматически в начале каждого раунда
- Лимит зависит от уровня Дара

**Combat Tokens:**
- Генерируются от экипировки, статов и событий боя
- Пример: Успешное уклонение может дать `tempo`
- Сгорают или переносятся в зависимости от правил

### Проверка возможности использования
```python
def can_use_ability(actor: ActorSnapshot, ability: AbilityDTO) -> bool:
    # 1. Проверка энергии и HP
    if actor.meta.en < ability.cost_energy:
        return False
    if actor.meta.hp < ability.cost_hp:
        return False
    
    # 2. Проверка токенов
    for token_type, cost in ability.cost_tokens.items():
        current = actor.meta.tokens.get(token_type, 0)
        if current < cost:
            return False
    
    return True
```

### Использование в бою
```python
# TurnManager
move = CombatMoveDTO(
    strategy="instant",
    payload={
        "skill_id": "fireball",
        "target_id": "all_enemies"
    }
)

# ContextBuilder
ability = get_ability_config("fireball")
ctx.flags.update(ability.flags)

# MechanicsService (списание ресурсов)
actor.meta.en -= ability.cost_energy
for token_type, cost in ability.cost_tokens.items():
    actor.meta.tokens[token_type] -= cost

# AbilityService (применение эффектов)
for effect in ability.effects:
    if effect.trigger == "on_hit" and result.is_hit:
        apply_effect(target, effect.params["status_id"])
```

---

## Хранение
```python
# abilities/__init__.py
ABILITY_REGISTRY: dict[str, AbilityDTO] = {}

def get_ability_config(ability_id: str) -> AbilityDTO | None:
    return ABILITY_REGISTRY.get(ability_id)

def get_all_abilities() -> list[AbilityDTO]:
    return list(ABILITY_REGISTRY.values())

def get_abilities_by_source(source: AbilitySource) -> list[AbilityDTO]:
    return [a for a in ABILITY_REGISTRY.values() if a.source == source]
```