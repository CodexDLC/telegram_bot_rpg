# Combat Integration (Интеграция с боевой системой)

## 📋 Обзор

Этот документ описывает, как предметы из инвентаря попадают в боевую систему RBC v3.1 и влияют на характеристики персонажа во время сражения.

**Ключевой принцип:** Предметы не участвуют в бою напрямую. Они превращаются в числовые модификаторы, которые хранятся в Redis и обрабатываются StatsEngine.

---

## 🏗️ Архитектура потока данных

```
┌─────────────────────┐
│  PostgreSQL (БД)    │
│  InventoryItemDTO   │ ← Полные данные предмета
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  ContextAssembler   │ ← Извлекает статы перед боем
│  (Player/Monster)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Redis (v:raw)      │ ← Только числа и модификаторы
│  Combat Context     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  StatsEngine        │ ← Считает итоговые статы
│  (Combat)           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  CombatResolver     │ ← Применяет триггеры
│  (Damage/Effects)   │
└─────────────────────┘
```

---

## 🔄 Этап 1: Загрузка из БД

### InventoryItemDTO (Полные данные)

**Место хранения:** PostgreSQL, таблица `inventory_items`

**Структура:**
```python
WeaponItemDTO(
    inventory_id=123,
    character_id=1,
    location="equipped",
    equipped_slot="main_hand",
    subtype="sword",
    rarity=ItemRarity.RARE,
    
    item_type=ItemType.WEAPON,
    data=WeaponData(
        name="Железный меч <Vampirism>",
        power=15.0,
        spread=0.2,
        accuracy=0.05,
        crit_chance=0.1,
        triggers=["trigger_bleed"],
        bonuses={
            "trigger_vampirism": True,
            "physical_damage_bonus": 0.05
        }
    )
)
```

### Запрос данных

**Кто запрашивает:** `ContextAssembler` (PlayerAssembler / MonsterAssembler)

**Код:**
```python
# apps/game_core/system/context_assembler/logic/player_assembler.py

async def process_batch(self, ids: list[int], scope: str):
    # Загружаем экипировку
    equipped_items = await self.inv_repo.get_items_by_location_batch(
        ids, 
        "equipped"
    )
    
    # equipped_items = {
    #     1: [WeaponItemDTO(...), ArmorItemDTO(...)],
    #     2: [WeaponItemDTO(...)]
    # }
```

---

## ⚙️ Этап 2: ContextAssembler (Трансформация)

### Назначение
Превратить полные данные предмета в компактные модификаторы для боя.

### Файл
`apps/game_core/system/context_assembler/schemas/combat.py`

### Метод: combat_view()

```python
@computed_field(alias="math_model")
def combat_view(self) -> dict[str, Any]:
    """
    Проекция для COMBAT SERVICE.
    Структура 'raw' для Redis.
    """
    model: dict[str, Any] = {
        "attributes": {},   # Базовые статы (сила, ловкость)
        "modifiers": {},    # Вторичные статы (урон, броня)
        "skills": {},       # Уровни скиллов
    }
    
    # ... Обработка экипировки ...
```

---

### Обработка предметов

#### Шаг 1: Определение руки

```python
for item in self.core_inventory:
    if item.location != "equipped":
        continue
    
    equipped_slot = item.equipped_slot
    prefix = ""
    
    if equipped_slot == "main_hand":
        prefix = "main_hand_"
    elif equipped_slot == "off_hand":
        prefix = "off_hand_"
    # Для 2H оружия: тоже "main_hand_"
```

**Зачем префикс?**
Чтобы различать статы левой и правой руки:
- `main_hand_damage_base` — урон правой руки
- `off_hand_damage_base` — урон левой руки

#### Шаг 2: Извлечение явных полей

**Для оружия (WeaponData):**
```python
data_json = item.data.model_dump()

# Power → damage_base
power = data_json.get("power")
if power is not None:
    self._add_modifier(model, f"{prefix}damage_base", src_key, power)

# Spread → damage_spread
spread = data_json.get("spread")
if spread is not None:
    self._add_modifier(model, f"{prefix}damage_spread", src_key, spread)

# Accuracy → accuracy
accuracy = data_json.get("accuracy")
if accuracy is not None:
    self._add_modifier(model, f"{prefix}accuracy", src_key, accuracy)

# Crit Chance → crit_chance
crit = data_json.get("crit_chance")
if crit is not None:
    self._add_modifier(model, f"{prefix}crit_chance", src_key, crit)
```

**Для брони (ArmorData):**
```python
# Power → damage_reduction_flat
power = data_json.get("power")
if power is not None:
    self._add_modifier(model, "damage_reduction_flat", src_key, power)

# Evasion Penalty → dodge_chance (отрицательный)
evasion_pen = data_json.get("evasion_penalty")
if evasion_pen is not None:
    self._add_modifier(model, "dodge_chance", src_key, f"{-evasion_pen}")
```

#### Шаг 3: Обработка бонусов (implicit + explicit)

```python
# Implicit Bonuses (от материала/базы)
implicit = data_json.get("implicit_bonuses") or {}
for stat, val in implicit.items():
    final_stat = f"{prefix}{stat}" if stat in HAND_DEPENDENT_STATS else stat
    self._add_modifier(model, final_stat, src_key, val)

# Explicit Bonuses (от аффиксов)
explicit = data_json.get("bonuses") or {}
for stat, val in explicit.items():
    final_stat = f"{prefix}{stat}" if stat in HAND_DEPENDENT_STATS else stat
    self._add_modifier(model, final_stat, src_key, val)
```

**HAND_DEPENDENT_STATS:**
```python
HAND_DEPENDENT_STATS = {
    "damage_base",
    "damage_spread",
    "damage_bonus",
    "penetration",
    "accuracy",
    "crit_chance",
}
```

#### Шаг 4: Форматирование значений

**Хелпер:** `format_value(key, value, source_type)`

```python
def _add_modifier(self, model: dict, stat_key: str, source_key: str, value: Any):
    # Преобразуем значение в строку для simpleeval
    val_str = format_value(stat_key, value, "external")
    
    if stat_key in model["attributes"]:
        model["attributes"][stat_key]["source"][source_key] = val_str
    else:
        if stat_key not in model["modifiers"]:
            model["modifiers"][stat_key] = {
                "base": 0.0,
                "source": {},
                "temp": {},
            }
        model["modifiers"][stat_key]["source"][source_key] = val_str
```

**Правила форматирования (из utils.py):**

```python
# 1. Атрибуты от предметов → Сложение (+)
if key in ATTRIBUTE_KEYS:  # strength, agility, ...
    return f"{value:+}"    # "+2"

# 2. Базовый урон/броня → Сложение (+)
if key in BASE_EQUIPMENT_KEYS:  # damage_base, protection
    return f"{value:+}"         # "+15"

# 3. Остальное → Умножение (*)
if -1.0 < value < 5.0:
    final_val = 1.0 + value
    return f"*{final_val:.4f}"  # "*1.0500"

# 4. Огромные значения → Сложение (Legacy)
return f"{value:+}"
```

---

### Примеры трансформации

#### Пример 1: Железный меч (базовый)

**Входные данные (WeaponData):**
```python
{
    "power": 15.0,
    "spread": 0.2,
    "accuracy": 0.05,
    "crit_chance": 0.1,
    "implicit_bonuses": {},
    "bonuses": {}
}
```

**Выходные данные (Redis v:raw):**
```python
{
    "modifiers": {
        "main_hand_damage_base": {
            "base": 0.0,
            "source": {
                "item:123": "+15"        # ← Сложение
            },
            "temp": {}
        },
        "main_hand_damage_spread": {
            "base": 0.0,
            "source": {
                "item:123": "+0.2"
            },
            "temp": {}
        },
        "main_hand_accuracy": {
            "base": 0.0,
            "source": {
                "item:123": "+0.05"
            },
            "temp": {}
        },
        "main_hand_crit_chance": {
            "base": 0.0,
            "source": {
                "item:123": "*1.1000"    # ← Умножение
            },
            "temp": {}
        }
    }
}
```

#### Пример 2: Меч с аффиксом (+5% урона)

**Входные данные:**
```python
{
    "power": 15.0,
    "spread": 0.2,
    "bonuses": {
        "physical_damage_bonus": 0.05
    }
}
```

**Выходные данные:**
```python
{
    "modifiers": {
        "main_hand_damage_base": {
            "source": {"item:123": "+15"}
        },
        "main_hand_damage_spread": {
            "source": {"item:123": "+0.2"}
        },
        "main_hand_physical_damage_bonus": {
            "source": {"item:123": "*1.0500"}  # ← 1 + 0.05
        }
    }
}
```

#### Пример 3: Кольцо силы (+2 STR)

**Входные данные (AccessoryData):**
```python
{
    "bonuses": {
        "strength": 2.0
    }
}
```

**Выходные данные:**
```python
{
    "attributes": {
        "strength": {
            "base": 10.0,  # Базовое значение персонажа
            "source": {
                "item:456": "+2"  # ← Сложение (атрибуты всегда +)
            }
        }
    }
}
```

---

## 💾 Этап 3: Сохранение в Redis

### Структура ключа

```
temp:setup:{uuid}
```

**Пример:**
```
temp:setup:a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### Содержимое (JSON)

```json
{
  "math_model": {
    "attributes": {
      "strength": {
        "base": 10.0,
        "source": {
          "item:456": "+2"
        },
        "temp": {}
      }
    },
    "modifiers": {
      "main_hand_damage_base": {
        "base": 0.0,
        "source": {
          "item:123": "+15"
        },
        "temp": {}
      },
      "main_hand_physical_damage_bonus": {
        "base": 0.0,
        "source": {
          "item:123": "*1.0500"
        },
        "temp": {}
      }
    },
    "skills": {}
  },
  "loadout": {
    "belt": [],
    "abilities": [],
    "equipment_layout": {
      "main_hand": "skill_swords"
    },
    "tags": ["player"]
  },
  "vitals": {
    "hp_current": 100,
    "energy_current": 100
  },
  "meta": {
    "entity_id": 1,
    "type": "player",
    "timestamp": 1704067200
  }
}
```

---

## 🧮 Этап 4: StatsEngine (Расчёт)

### Назначение
Считает итоговые значения статов, объединяя все модификаторы.

### Файл
`apps/game_core/modules/combat/combat_engine/logic/stats_engine.py`

### Алгоритм

```python
def calculate_final_stat(stat_key: str, raw_data: dict) -> float:
    """
    Считает итоговое значение стата.
    """
    base = raw_data.get("base", 0.0)
    sources = raw_data.get("source", {})
    temps = raw_data.get("temp", {})
    
    # 1. Собираем все модификаторы
    all_mods = list(sources.values()) + list(temps.values())
    
    # 2. Разделяем на + и *
    additive = []
    multiplicative = []
    
    for mod_str in all_mods:
        if mod_str.startswith("+") or mod_str.startswith("-"):
            additive.append(float(mod_str))
        elif mod_str.startswith("*"):
            multiplicative.append(float(mod_str[1:]))
    
    # 3. Применяем сложение
    result = base + sum(additive)
    
    # 4. Применяем умножение
    for mult in multiplicative:
        result *= mult
    
    return result
```

### Пример расчёта

**Входные данные:**
```python
{
    "main_hand_damage_base": {
        "base": 0.0,
        "source": {
            "item:123": "+15",       # Меч
            "buff:strength": "+5"    # Бафф силы
        }
    },
    "main_hand_physical_damage_bonus": {
        "base": 0.0,
        "source": {
            "item:123": "*1.0500",   # +5% от аффикса
            "skill:swords": "*1.1000" # +10% от скилла
        }
    }
}
```

**Расчёт:**
```python
# Damage Base
base = 0.0
additive = [15, 5]
result = 0 + 15 + 5 = 20

# Physical Damage Bonus
base = 0.0
multiplicative = [1.05, 1.10]
result = 1.0 * 1.05 * 1.10 = 1.155 (15.5% бонуса)

# Итоговый урон
final_damage = 20 * 1.155 = 23.1
```

---

## ⚔️ Этап 5: CombatResolver (Триггеры)

### Назначение
Применяет триггеры оружия во время атаки.

### Файл
`apps/game_core/modules/combat/combat_engine/logic/combat_resolver.py`

### Как триггеры попадают в бой?

**1. WeaponData.triggers не сохраняются в v:raw**

Триггеры НЕ попадают в math_model. Они хранятся отдельно в `loadout`:

```json
{
  "loadout": {
    "equipment_layout": {
      "main_hand": "skill_swords"
    }
  }
}
```

**Проблема:** Триггеры потеряны! Нужно добавить:

```json
{
  "loadout": {
    "equipment_layout": {
      "main_hand": "skill_swords"
    },
    "weapon_triggers": {
      "main_hand": ["trigger_bleed"],
      "off_hand": []
    }
  }
}
```

**2. ContextBuilder извлекает триггеры**

```python
# apps/game_core/modules/combat/combat_engine/logic/context_builder.py

def build_action_context(actor_id: str, action: ActionDTO) -> ActionContext:
    # Загружаем loadout
    loadout = redis.get_json(f"combat:actor:{actor_id}:loadout")
    
    # Извлекаем триггеры оружия
    weapon_triggers = loadout.get("weapon_triggers", {}).get("main_hand", [])
    
    # Создаём контекст
    ctx = ActionContext(
        attacker_id=actor_id,
        triggers={t: True for t in weapon_triggers}
    )
    
    return ctx
```

**3. CombatResolver проверяет триггеры**

```python
async def resolve_attack(ctx: ActionContext) -> ResolveResult:
    # Расчёт урона
    damage = calculate_damage(ctx)
    is_crit = random.random() < ctx.attacker.crit_chance
    
    # Проверка триггеров
    mutations = []
    
    if is_crit and ctx.triggers.get("trigger_bleed"):
        mutations.append(
            Mutation(
                type="add_status_effect",
                target=ctx.defender_id,
                data={
                    "effect_id": "bleed",
                    "damage_per_turn": 5,
                    "duration": 3
                }
            )
        )
    
    return ResolveResult(damage=damage, mutations=mutations)
```

---

## 🔧 Необходимые изменения

### 1. Добавить weapon_triggers в loadout

**Файл:** `apps/game_core/system/context_assembler/schemas/combat.py`

**Текущий код:**
```python
@computed_field(alias="loadout")
def loadout_view(self) -> dict[str, Any]:
    equipment_layout = {}
    
    for item in self.core_inventory:
        if item.location == "equipped":
            slot = item.equipped_slot
            skill_key = item.data.related_skill
            equipment_layout[slot] = skill_key
    
    return {
        "equipment_layout": equipment_layout,
        "belt": [],
        "abilities": [],
        "tags": ["player"]
    }
```

**Новый код:**
```python
@computed_field(alias="loadout")
def loadout_view(self) -> dict[str, Any]:
    equipment_layout = {}
    weapon_triggers = {
        "main_hand": [],
        "off_hand": []
    }
    
    for item in self.core_inventory:
        if item.location == "equipped":
            slot = item.equipped_slot
            skill_key = item.data.related_skill
            equipment_layout[slot] = skill_key
            
            # Извлекаем триггеры оружия
            if item.item_type == "weapon" and hasattr(item.data, "triggers"):
                if slot in ["main_hand", "off_hand"]:
                    weapon_triggers[slot] = item.data.triggers
    
    return {
        "equipment_layout": equipment_layout,
        "weapon_triggers": weapon_triggers,  # ← НОВОЕ
        "belt": [],
        "abilities": [],
        "tags": ["player"]
    }
```

### 2. Добавить trigger bonuses в loadout

**Для триггеров от аффиксов:**

```python
# В loadout добавляем
"trigger_bonuses": {
    "trigger_vampirism": True,
    "trigger_fire": True
}
```

**Извлечение:**
```python
# Собираем триггеры из bonuses
for item in self.core_inventory:
    if item.location == "equipped":
        bonuses = item.data.bonuses or {}
        for key, val in bonuses.items():
            if key.startswith("trigger_") and val is True:
                trigger_bonuses[key] = True
```

---

## 📊 Полный пример интеграции

### Предмет в БД

```python
WeaponItemDTO(
    inventory_id=123,
    item_type=ItemType.WEAPON,
    equipped_slot="main_hand",
    data=WeaponData(
        name="Железный меч <Vampirism>",
        power=15.0,
        spread=0.2,
        triggers=["trigger_bleed"],
        bonuses={
            "trigger_vampirism": True,
            "physical_damage_bonus": 0.05
        }
    )
)
```

### Redis v:raw (после ContextAssembler)

```json
{
  "math_model": {
    "modifiers": {
      "main_hand_damage_base": {
        "source": {"item:123": "+15"}
      },
      "main_hand_damage_spread": {
        "source": {"item:123": "+0.2"}
      },
      "main_hand_physical_damage_bonus": {
        "source": {"item:123": "*1.0500"}
      }
    }
  },
  "loadout": {
    "weapon_triggers": {
      "main_hand": ["trigger_bleed"]
    },
    "trigger_bonuses": {
      "trigger_vampirism": true
    }
  }
}
```

### В бою (CombatResolver)

```python
# Загружаем контекст
loadout = redis.get_json("combat:actor:player_1:loadout")

# Извлекаем триггеры
weapon_triggers = loadout["weapon_triggers"]["main_hand"]
# ["trigger_bleed"]

trigger_bonuses = loadout["trigger_bonuses"]
# {"trigger_vampirism": true}

# Создаём контекст атаки
ctx = ActionContext(
    triggers={
        "trigger_bleed": True,
        "trigger_vampirism": True
    }
)

# Разрешаем атаку
if is_crit and ctx.triggers.get("trigger_bleed"):
    apply_bleed(target)

if ctx.triggers.get("trigger_vampirism"):
    heal_attacker(ctx.damage * 0.15)
```

---

## 📚 Связанная документация

- **Система предметов:** [README.md](../../rpg_system/items/README.md)
- **DTO справочник:** [01_item_dto_reference.md](./01_item_dto_reference.md)
- **Триггеры:** [weapon_triggers/README.md](./weapon_triggers/README.md)
- **ContextAssembler:** `/docs/architecture/game_core_services/context_assembler_v2/`
- **Боевая система:** `/docs/architecture/combat_system_v3/`

---

**Последнее обновление:** Январь 2026  
**Статус:** Требуется доработка weapon_triggers и trigger_bonuses в loadout