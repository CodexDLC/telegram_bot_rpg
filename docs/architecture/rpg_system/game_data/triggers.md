# Weapon Triggers (Триггеры оружия)

## 📋 Обзор

Триггеры оружия — это специальные эффекты, которые срабатывают при определенных условиях (обычно при критическом ударе) и зависят от типа используемого оружия.

**Философия:**
Критический удар сам по себе является триггером.
*   **Стандартный крит:** Это триггер с эффектом "Умножение урона" (обычно x2).
*   **Специфичные триггеры:** Оружие может иметь свои уникальные триггеры, которые могут:
    *   Заменять стандартный множитель урона на другой эффект (например, Stun).
    *   Добавлять эффект к стандартному множителю.
    *   Изменять сам множитель (например, x3 вместо x2).

**Ключевое правило:**
Триггер определяет, что происходит при событии `ON_CRIT`. Если триггер устанавливает `crit_damage_boost = False`, то стандартное умножение урона отключается в пользу эффекта триггера.

## ⚙️ Техническая реализация

### Структура DTO

```python
from pydantic import BaseModel
from typing import Any

class TriggerDTO(BaseModel):
    trigger_id: str             # Уникальный ID (например, "sword_crit_bleed")
    weapon_class: str           # Класс оружия ("skill_swords", "skill_macing")
    
    event: str                  # Событие: "ON_CRIT", "ON_HIT", "ON_DODGE"
    flag_name: str              # Имя флага в контексте ("trigger_bleed")
    effect_id: str | None       # ID эффекта для наложения ("bleed") или None
    
    # Мутации контекста при срабатывании
    # Пример: {"crit_damage_boost": False}
    mutations: dict[str, Any] = {}
    
    description: str
```

### Примеры конфигурации

#### 1. Heavy Strike (x3 Damage)
Триггер, который просто дает огромный урон, но не накладывает эффектов.
Используется для **Polearms** (Древковое), так как Axes удалены.

```python
heavy_crit_trigger = TriggerDTO(
    trigger_id="polearm_heavy_crit",
    weapon_class="skill_polearms",  # Исправлено: skill_axes -> skill_polearms
    event="ON_CRIT",
    flag_name="trigger_heavy_crit",
    effect_id=None,
    mutations={
        "crit_damage_boost": True,   # Оставляем буст урона
        "crit_multiplier": 3.0       # Но меняем множитель на x3
    },
    description="Сокрушительный удар алебардой, наносящий тройной урон."
)
```

#### 2. Bleed (No Bonus Damage)
Крит мечом не наносит двойной урон, но вызывает сильное кровотечение.

```python
sword_trigger = TriggerDTO(
    trigger_id="sword_crit_bleed",
    weapon_class="skill_swords",
    event="ON_CRIT",
    flag_name="trigger_bleed",
    effect_id="bleed",
    mutations={"crit_damage_boost": False}, # Отключаем стандартный x2
    description="Критический удар накладывает глубокое кровотечение вместо бонуса урона."
)
```

#### 3. Stun (No Bonus Damage)
Крит молотом оглушает цель, но не наносит двойной урон.

```python
mace_trigger = TriggerDTO(
    trigger_id="macing_crit_stun",
    weapon_class="skill_macing",
    event="ON_CRIT",
    flag_name="trigger_stun",
    effect_id="stun",
    mutations={"crit_damage_boost": False}, # Отключаем стандартный x2
    description="Критический удар оглушает цель, сбивая дыхание."
)
```

## 🔌 Интеграция в боевую систему

### 1. Загрузка триггера (ContextBuilder)
Перед расчетом удара система определяет, какой триггер связан с оружием атакующего.

```python
# Определяем навык оружия (например, "skill_swords")
weapon_skill = actor.loadout.layout.get("main_hand") 

# Ищем триггер
trigger = get_weapon_trigger(weapon_skill)
if trigger:
    # Устанавливаем флаг готовности триггера
    setattr(ctx.triggers, trigger.flag_name, True)
```

### 2. Резолвинг (CombatResolver)
В момент наступления события (например, `is_crit == True`) применяются мутации.

```python
if result.is_crit:
    # Применяем логику триггера
    CombatResolver._resolve_triggers(ctx, result, "ON_CRIT")
    
    # Логика внутри _resolve_triggers:
    # Если trigger.mutations["crit_damage_boost"] == False -> result.crit_mod = 1.0
    # Если trigger.mutations["crit_multiplier"] == 3.0 -> result.crit_mod = 3.0
```

### 3. Наложение эффектов (AbilityService / Post-Process)
После расчета урона, если триггер сработал и у него есть `effect_id`, накладывается эффект.

```python
if ctx.triggers.trigger_bleed and result.is_crit:
    apply_effect(target, "bleed")
```

## 📦 Registry & Rules

### TRIGGER_RULES
Словарь правил для быстрой проверки мутаций внутри резолвера.

```python
TRIGGER_RULES = {
    "ON_CRIT": {
        "trigger_bleed": {
            "chance": 1.0,
            "mutations": {"crit_damage_boost": False}
        },
        "trigger_heavy_crit": {
            "chance": 1.0,
            "mutations": {"crit_damage_boost": True, "crit_multiplier": 3.0}
        }
    }
}
```

### Registry Access
```python
# apps/game_core/resources/game_data/triggers/__init__.py

TRIGGER_REGISTRY: dict[str, TriggerDTO] = {
    "sword_crit_bleed": sword_trigger,
    "polearm_heavy_crit": heavy_crit_trigger,
    # ...
}

def get_weapon_trigger(weapon_class: str) -> TriggerDTO | None:
    """Поиск триггера по классу оружия."""
    for trigger in TRIGGER_REGISTRY.values():
        if trigger.weapon_class == weapon_class:
            return trigger
    return None
```
