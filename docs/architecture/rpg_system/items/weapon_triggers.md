# Weapon Triggers System (Система триггеров оружия)

## 📋 Обзор

Триггеры — это условные эффекты, которые срабатывают во время боя в ответ на определённые события (крит, попадание, парирование).

**Ключевая идея:** Оружие влияет на бой не только через урон, но и через уникальные механики.

---

## 🎯 Философия системы

### 1. Триггеры ≠ Активные способности
- Триггер **не требует действия игрока** — срабатывает автоматически при выполнении условия
- Триггер **привязан к оружию** — меняешь меч на топор → меняется механика

### 2. Триггеры — часть идентичности оружия
- **Мечи (Swords):** Кровотечение (Bleed) — DoT эффект
- **Луки (Archery):** Уворот после выстрела (Hit & Run)
- **Булавы (Macing):** Оглушение (Stun) — контроль
- **Рапиры (Fencing):** Игнорирование брони (Armor Bypass)

### 3. Только у оружия
- **Броня, аксессуары** — триггеров НЕ имеют
- **Щиты** — триггеры работают через **скиллы** (парирование), а не через предмет

---

## 🏗️ Архитектура

### Где хранятся триггеры?

```
1. BaseItemDTO (база оружия)
   ├─ triggers: ["trigger_bleed"]  ← Встроенный триггер типа оружия
   
2. Affixes (аффиксы/заточка)
   ├─ bonuses: {"trigger_vampirism": True}  ← Магический триггер
   
3. WeaponData (итоговый предмет)
   ├─ triggers: ["trigger_bleed"]           ← От базы
   └─ bonuses: {"trigger_vampirism": True}  ← От аффикса
```

### Как триггеры попадают в бой?

```
ItemAssembler
    ↓
WeaponData.triggers = ["trigger_bleed"]
WeaponData.bonuses = {"trigger_vampirism": True}
    ↓
ContextAssembler (перед боем)
    ↓
Redis v:raw (боевой контекст)
    ↓
ContextBuilder (в момент атаки)
    ↓
ctx.triggers.trigger_bleed = True
ctx.triggers.trigger_vampirism = True
    ↓
CombatResolver (проверка условий)
    ↓
if ctx.triggers.trigger_bleed and event == "ON_CRIT":
    apply_bleed_effect(target)
```

---

## 📊 Структура TriggerRegistry

### Формат триггера

```python
TRIGGER_REGISTRY = {
    "trigger_bleed": {
        "event": "ON_CRIT",           # Когда срабатывает
        "chance": 1.0,                 # Шанс срабатывания (1.0 = 100%)
        "effect": "apply_bleed",       # Что делает
        "metadata": {                  # Параметры эффекта
            "damage_per_turn": 5,
            "duration": 3,
            "stack_limit": 3
        }
    },
    
    "trigger_vampirism": {
        "event": "ON_HIT",
        "chance": 1.0,
        "effect": "heal_attacker",
        "metadata": {
            "heal_percent": 0.15       # 15% от урона
        }
    },
    
    "trigger_armor_breach": {
        "event": "ON_CRIT",
        "chance": 1.0,
        "effect": "ignore_armor",
        "metadata": {
            "armor_ignored_percent": 1.0  # 100%
        }
    }
}
```

### События (Events)

| Event        | Описание                                   |
|--------------|--------------------------------------------|
| `ON_HIT`     | При любом попадании                        |
| `ON_CRIT`    | При критическом ударе                      |
| `ON_MISS`    | При промахе                                |
| `ON_PARRY`   | При парировании (защитник парировал атаку) |
| `ON_DODGE`   | При уворотах (цель увернулась)             |
| `ON_KILL`    | При убийстве врага                         |

---

## ⚔️ Категории оружия и их триггеры

### 1. Swords (Мечи) — Bleed
**Философия:** Режущие раны → кровотечение.

**Примеры:**
- **Longsword:** `trigger_bleed` (DoT)
- **Katana:** `trigger_heavy_bleed` (усиленный DoT)
- **Flamberge:** `trigger_extended_bleed` (длительность +1)

**Реализация:**
```python
"trigger_bleed": {
    "event": "ON_CRIT",
    "effect": "apply_bleed",
    "metadata": {
        "damage_per_turn": 5,
        "duration": 3
    }
}
```

---

### 2. Archery (Стрелковое) — Tactical
**Философия:** Дистанция + мобильность.

**Примеры:**
- **Shortbow:** `trigger_evasive_shot` (бафф уворота после выстрела)
- **Longbow:** `trigger_sniper_crit` (крит x3 вместо x2)
- **Heavy Crossbow:** `trigger_armor_pierce` (игнор брони)

**Реализация:**
```python
"trigger_evasive_shot": {
    "event": "ON_HIT",
    "effect": "buff_dodge",
    "metadata": {
        "dodge_tokens": 2,
        "duration": 1
    }
}

"trigger_sniper_crit": {
    "event": "ON_CRIT",
    "effect": "multiply_damage",
    "metadata": {
        "multiplier": 3.0
    }
}
```

---

### 3. Macing (Дробящее) — Control
**Философия:** Кинетическая энергия → оглушение.

**Примеры:**
- **Mace:** `trigger_macing_stun` (оглушение на 1 ход)
- **War Hammer:** `trigger_armor_crush` (снижение брони до конца боя)
- **Flail:** `trigger_shield_bypass` (игнор блока щитом)

**Реализация:**
```python
"trigger_macing_stun": {
    "event": "ON_CRIT",
    "effect": "apply_stun",
    "metadata": {
        "duration": 1
    }
}

"trigger_armor_crush": {
    "event": "ON_CRIT",
    "effect": "reduce_armor",
    "metadata": {
        "armor_reduction": 0.5,  # -50% flat armor
        "duration": 99           # До конца боя
    }
}
```

---

### 4. Fencing (Фехтование) — Precision
**Философия:** Точность + игнорирование защиты.

**Примеры:**
- **Rapier:** `trigger_vitals_trace` (игнор % резиста)
- **Stiletto:** `trigger_needle_point` (игнор flat armor)
- **Dagger (Off-hand):** `trigger_blade_catcher` (контратака после парирования)

**Реализация:**
```python
"trigger_vitals_trace": {
    "event": "ON_CRIT",
    "effect": "ignore_resistance",
    "metadata": {
        "resistance_ignored_percent": 1.0
    }
}

"trigger_blade_catcher": {
    "event": "ON_PARRY",
    "effect": "grant_counter_token",
    "metadata": {
        "counter_tokens": 1
    }
}
```

---

### 5. Polearms (Древковое) — Distance Control
**Философия:** Длина оружия → контроль дистанции.

**Примеры:**
- **Pike:** `trigger_piercing_thrust` (игнор резиста)
- **Halberd:** `trigger_armor_crush` (снижение брони)
- **Trident:** `trigger_entangle` (Root, обездвиживание)

**Реализация:**
```python
"trigger_piercing_thrust": {
    "event": "ON_CRIT",
    "effect": "ignore_resistance",
    "metadata": {
        "resistance_ignored_percent": 1.0
    }
}

"trigger_entangle": {
    "event": "ON_HIT",
    "chance": 0.3,  # 30% шанс
    "effect": "apply_root",
    "metadata": {
        "duration": 1
    }
}
```

---

## 🔧 Реализация в коде

### 1. Определение триггеров (game_data/triggers/)

```python
# apps/game_core/resources/game_data/triggers/definitions/weapon_triggers.py

from apps.game_core.resources.game_data.triggers.schemas import TriggerData

WEAPON_TRIGGERS: dict[str, TriggerData] = {
    "trigger_bleed": TriggerData(
        id="trigger_bleed",
        name_ru="Кровотечение",
        event="ON_CRIT",
        chance=1.0,
        effect="apply_bleed",
        metadata={
            "damage_per_turn": 5,
            "duration": 3,
            "stack_limit": 3
        }
    ),
    
    "trigger_vampirism": TriggerData(
        id="trigger_vampirism",
        name_ru="Вампиризм",
        event="ON_HIT",
        chance=1.0,
        effect="heal_attacker",
        metadata={
            "heal_percent": 0.15
        }
    ),
    
    # ... остальные триггеры
}
```

### 2. Регистрация в базе оружия (base_item/weapons/)

```python
# apps/game_core/resources/game_data/items/base_item/weapons/swords.py

from apps.game_core.resources.game_data.items.schemas import BaseItemDTO

SWORDS_DB = {
    "longsword": BaseItemDTO(
        id="longsword",
        name_ru="Длинный меч",
        slot="main_hand",
        type="weapon",
        
        base_power=10,
        base_durability=100,
        damage_spread=0.2,
        
        allowed_materials=["ingots"],
        
        triggers=["trigger_bleed"],  # ← Встроенный триггер
        
        narrative_tags=["blade", "versatile"]
    ),
    
    "katana": BaseItemDTO(
        id="katana",
        name_ru="Катана",
        slot="main_hand",
        type="weapon",
        
        base_power=12,
        base_durability=80,
        damage_spread=0.15,
        
        allowed_materials=["ingots"],
        
        triggers=["trigger_heavy_bleed"],  # ← Усиленный триггер
        
        narrative_tags=["blade", "precise", "exotic"]
    )
}
```

### 3. Применение в бою (combat/logic/combat_resolver.py)

```python
# apps/game_core/modules/combat/combat_engine/logic/combat_resolver.py

async def resolve_attack(ctx: ActionContext) -> ResolveResult:
    """
    Разрешение атаки с учётом триггеров.
    """
    # 1. Расчёт попадания/уворотов
    hit_roll = random.random()
    if hit_roll > ctx.attacker.accuracy:
        return ResolveResult(outcome="miss")
    
    # 2. Расчёт урона
    damage = calculate_damage(ctx)
    
    # 3. Проверка крита
    is_crit = random.random() < ctx.attacker.crit_chance
    if is_crit:
        damage *= ctx.attacker.crit_power
    
    # 4. Применение триггеров
    mutations = []
    
    # ON_HIT триггеры (всегда срабатывают при попадании)
    for trigger_id in ctx.attacker.triggers:
        trigger = WEAPON_TRIGGERS.get(trigger_id)
        if not trigger:
            continue
        
        if trigger.event == "ON_HIT":
            if random.random() <= trigger.chance:
                effect = apply_trigger_effect(trigger, ctx)
                mutations.append(effect)
    
    # ON_CRIT триггеры (только при крите)
    if is_crit:
        for trigger_id in ctx.attacker.triggers:
            trigger = WEAPON_TRIGGERS.get(trigger_id)
            if not trigger:
                continue
            
            if trigger.event == "ON_CRIT":
                if random.random() <= trigger.chance:
                    effect = apply_trigger_effect(trigger, ctx)
                    mutations.append(effect)
    
    # 5. Применение мутаций
    for mutation in mutations:
        await apply_mutation(ctx, mutation)
    
    return ResolveResult(
        outcome="hit" if not is_crit else "crit",
        damage=damage,
        mutations=mutations
    )


def apply_trigger_effect(trigger: TriggerData, ctx: ActionContext) -> Mutation:
    """
    Преобразует триггер в мутацию (изменение состояния).
    """
    effect_type = trigger.effect
    metadata = trigger.metadata
    
    if effect_type == "apply_bleed":
        return Mutation(
            type="add_status_effect",
            target=ctx.defender.actor_id,
            data={
                "effect_id": "bleed",
                "damage_per_turn": metadata["damage_per_turn"],
                "duration": metadata["duration"]
            }
        )
    
    elif effect_type == "heal_attacker":
        heal_amount = int(ctx.final_damage * metadata["heal_percent"])
        return Mutation(
            type="heal",
            target=ctx.attacker.actor_id,
            data={"amount": heal_amount}
        )
    
    elif effect_type == "ignore_armor":
        return Mutation(
            type="modify_defense",
            target=ctx.defender.actor_id,
            data={
                "flat_armor_multiplier": 0.0,  # Броня не работает
                "duration": "this_attack"
            }
        )
    
    # ... другие эффекты
    
    return Mutation(type="none")
```

---

## 🧪 Примеры использования

### Пример 1: Меч с кровотечением

```python
# Создание предмета
weapon = ItemAssembler.assemble_equipment(
    base_id="longsword",
    target_tier=2,
    bundle_id=None
)

# WeaponData
{
    "power": 15.0,
    "spread": 0.2,
    "triggers": ["trigger_bleed"],  # ← От базы
    "bonuses": {}
}

# В бою
# 1. Атака критует
# 2. CombatResolver проверяет ctx.triggers.trigger_bleed
# 3. trigger_bleed.event == "ON_CRIT" → срабатывает
# 4. Накладывается эффект Bleed на 3 хода
```

### Пример 2: Меч с вампиризмом (аффикс)

```python
# Создание предмета с аффиксом
weapon = ItemAssembler.assemble_equipment(
    base_id="longsword",
    target_tier=3,
    bundle_id="vampirism"  # ← Аффикс
)

# WeaponData
{
    "power": 20.0,
    "spread": 0.2,
    "triggers": ["trigger_bleed"],              # ← От базы
    "bonuses": {"trigger_vampirism": True}      # ← От аффикса
}

# В бою
# 1. Атака попадает
# 2. CombatResolver проверяет оба триггера
# 3. trigger_vampirism (ON_HIT) → восстанавливает HP
# 4. Если крит → trigger_bleed → кровотечение
```

### Пример 3: Тяжёлый арбалет (пробитие брони)

```python
# Создание предмета
weapon = ItemAssembler.assemble_equipment(
    base_id="heavy_crossbow",
    target_tier=4,
    bundle_id=None
)

# WeaponData
{
    "power": 30.0,
    "spread": 0.1,
    "triggers": ["trigger_armor_pierce"],  # ← От базы
    "bonuses": {}
}

# В бою
# 1. Атака попадает (ON_HIT)
# 2. trigger_armor_pierce → игнорирует 100% flat armor
# 3. Урон проходит сквозь броню
```

---

## 📚 Связанная документация

- **Дизайн триггеров по типам оружия:**
  - [archery.md](./archery.md) — Стрелковое
  - [fencing.md](./fencing.md) — Фехтование
  - [swords.md](./swords.md) — Мечи
  - [macing.md](./macing.md) — Дробящее
  - [polearms.md](./polearms.md) — Древковое

- **Система боя:** `/docs/architecture/combat_system_v3/`
- **Предметы:** `/docs/rpg_system/items/README.md`

---

## 🚧 TODO

- [ ] Создать `TriggerData` схему (Pydantic DTO)
- [ ] Реализовать `apply_trigger_effect()` для всех типов эффектов
- [ ] Добавить тесты для каждого триггера
- [ ] Документировать все триггеры в отдельных `.md` файлах
- [ ] Добавить UI-индикаторы триггеров в бою

---

**Последнее обновление:** Январь 2026  
**Статус:** Draft (требуется реализация кода)
