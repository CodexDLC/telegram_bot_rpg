# RPG Layer Overview (RBC v3.1)

⬅️ [Назад](./README.md)

Этот документ описывает связь между **Слоем RPG** (персонаж, инвентарь, прогрессия) и **Слоем Боя** (Combat Engine).

---

## 1. Три слоя системы
```
┌─────────────────────────────────────────────────────────┐
│                    RPG LAYER                            │
│  - Character Stats (Attributes, Skills)                 │
│  - Inventory (Items, Equipment)                         │
│  - Abilities (Known Skills, Feints)                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Context Assembler
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  COMBAT LAYER                           │
│  - Actor Snapshot (State, Raw, Loadout)                 │
│  - Combat Resolver (Math Engine)                        │
│  - Trigger System (Effects)                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ View Service
                     ▼
┌─────────────────────────────────────────────────────────┐
│                    UI LAYER                             │
│  - Dashboard (HP, Buttons)                              │
│  - Logs (Battle History)                                │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Как RPG влияет на бой

### 2.1. Оружие → Триггеры

**RPG Layer:**
```python
# Item Definition
BaseItemDTO(
    id="longsword",
    name_ru="Длинный меч",
    triggers=["trigger_bleed"],  # ← Определяет поведение крита
    implicit_bonuses={
        "physical_crit_chance": 0.05,
        "main_hand_damage_base": 15
    }
)
```

**Combat Layer:**
```python
# Context Builder
weapon = actor.loadout.get("main_hand")
for trigger_name in weapon.triggers:
    ctx.triggers.trigger_bleed = True  # Активация

# Resolver
if res.is_crit:
    _resolve_triggers(ctx, res, "ON_CRIT")
    # trigger_bleed → apply_bleed = True
```

---

### 2.2. Скиллы → Композиция триггеров

**RPG Layer:**
```python
# Ability Definition
{
    "skill_id": "devastating_strike",
    "name": "Разящий удар",
    "cost": 5,  # Tactical Tokens
    "triggers": [
        "trigger_force_crit",
        "trigger_armor_break"
    ],
    "raw_mutations": {
        "main_hand_damage_base": "*1.5"
    }
}
```

**Combat Layer:**
```python
# Ability Service (Pre-Calc)
for trigger in skill.triggers:
    setattr(ctx.triggers, trigger, True)

actor.raw.modifiers["main_hand_damage_base"]["temp"] = {"ability": "*1.5"}

# Resolver применяет триггеры и считает урон
```

---

### 2.3. Атрибуты → Базовые статы

**RPG Layer:**
```python
# Character
{
    "strength": 15,
    "agility": 12,
    "endurance": 10
}
```

**Combat Layer:**
```python
# Stats Engine (Waterfall Calculator)
final_damage = (
    base_weapon_damage +
    (strength * 1.5) +  # Derivation Rule
    equipment_bonuses
) * multipliers
```

---

## 3. Как Бой влияет на RPG

### 3.1. XP Buffer → Прогрессия навыков

**Combat Layer:**
```python
# Mechanics Service
if res.is_crit:
    actor.xp_buffer["crit_hits"] += 1
    
if res.is_dodged:
    target.xp_buffer["dodge_success"] += 1
```

**RPG Layer (Post-Battle):**
```python
# Награды
weapon_skill = actor.equipment["main_hand"].skill_class  # "skill_swords"

xp_gained = xp_buffer["crit_hits"] * 15  # 15 XP за крит

character.skills[weapon_skill] += xp_gained
```

---

### 3.2. Активные эффекты → Состояние персонажа

**Combat Layer:**
```python
# Ability Service
target.active_abilities.append(
    ActiveAbilityDTO(
        ability_id="bleed",
        expire_at_exchange=current + 3,
        impact={"hp": -10}  # Урон за тик
    )
)
```

**RPG Layer (UI):**
```python
# View Service
effects = [a.ability_id for a in actor.active_abilities]
# ["bleed", "poison", "haste"]

# Отображаем иконки в UI
```

---

## 4. Связующие компоненты

### 4.1. Context Assembler
**Роль:** Превращает RPG данные в Combat данные.
```python
# Input: Character ID
# Output: ActorSnapshot

def assemble_context(char_id):
    # 1. Load from SQL
    character = db.query(Character).get(char_id)
    equipment = db.query(Equipment).filter_by(char_id=char_id).all()
    
    # 2. Build Raw
    raw = {
        "attributes": character.attributes,
        "modifiers": calculate_equipment_bonuses(equipment)
    }
    
    # 3. Build Loadout
    loadout = {
        "layout": {"main_hand": "skill_swords", ...},
        "known_abilities": character.abilities
    }
    
    # 4. Save to Redis
    redis.json().set(f"combat:actor:{char_id}", "$", {
        "meta": {...},
        "raw": raw,
        "loadout": loadout
    })
```

---

### 4.2. View Service
**Роль:** Превращает Combat данные обратно в UI данные.
```python
# Input: BattleContext
# Output: CombatDashboardDTO

def build_dashboard(ctx, char_id):
    actor = ctx.actors[char_id]
    
    return CombatDashboardDTO(
        hero=ActorFullInfo(
            name=actor.meta.name,
            hp_current=actor.meta.hp,
            effects=[a.ability_id for a in actor.active_abilities]
        ),
        target=...,
        status="active"
    )
```

---

## 5. Ключевые принципы

### 5.1. Разделение ответственности
- **RPG Layer** = Постоянные данные (SQL, прогрессия)
- **Combat Layer** = Временные данные (Redis, состояние боя)
- **UI Layer** = Отображение (DTO, никакой бизнес-логики)

### 5.2. Односторонняя зависимость
```
RPG → Combat → UI
```

- Combat НЕ ЗНАЕТ про SQL
- UI НЕ ЗНАЕТ про Redis

### 5.3. Универсальность триггеров
Триггеры работают одинаково для:
- Оружия (RPG → Item Definition)
- Скиллов (RPG → Ability Config)
- Финтов (Combat → Tactical Moves)

Резолвер **НЕ ЗНАЕТ** источник триггера.

---

## 6. Примеры полного цикла

### Пример 1: Крит с кровотечением

**RPG → Combat:**
1. Игрок экипирует меч: `weapon.triggers = ["trigger_bleed"]`
2. Context Assembler загружает оружие в `actor.loadout`
3. Context Builder активирует триггер: `ctx.triggers.trigger_bleed = True`

**Combat (Расчёт):**
4. Resolver проверяет крит → `is_crit = True`
5. Resolver вызывает `_resolve_triggers("ON_CRIT")`
6. Триггер срабатывает → `result.ability_flags.apply_bleed = True`
7. Ability Service накладывает дебафф → `actor.active_abilities.append(...)`

**Combat → UI:**
8. View Service собирает список эффектов → `["bleed"]`
9. UI отображает иконку кровотечения

---

### Пример 2: Удар щитом (Shield Bash)

**RPG → Combat:**
1. Игрок использует скилл: `skill_id = "shield_bash"`
2. Ability Service читает конфиг:
```python
   {
       "cost": 3,
       "override_damage": (0, 0),
       "triggers": ["trigger_stun"]
   }
```

**Combat (Расчёт):**
3. Ability Service обнуляет урон: `ctx.override_damage = (0, 0)`
4. Ability Service активирует триггер: `ctx.triggers.trigger_stun = True`
5. Resolver считает урон → `damage_final = 0`
6. Resolver применяет триггер → `result.ability_flags.apply_stun = True`
7. Ability Service накладывает стан

**Combat → RPG:**
8. Mechanics Service записывает в XP: `xp_buffer["stuns_applied"] += 1`
9. После боя: `character.skills["skill_shield_mastery"] += xp`

---

## 7. Расширяемость

### Добавление нового оружия
1. Создать `BaseItemDTO` с триггером
2. Триггер УЖЕ ЕСТЬ в `TRIGGER_RULES` → работает сразу
3. Если триггера нет → добавить в `TRIGGER_RULES`

### Добавление нового скилла
1. Создать конфиг с `triggers` и `raw_mutations`
2. Ability Service активирует триггеры
3. Резолвер обрабатывает их

### Добавление нового эффекта
1. Добавить флаг в `AbilityFlagsDTO`
2. Добавить обработку в `AbilityService.post_process()`
3. Готово — эффект доступен для оружия И скиллов