# Item DTO Reference (Справочник DTO предметов)

## 📋 Обзор

Все предметы в игре представлены через полиморфные Pydantic DTO, которые обеспечивают:
- Типобезопасность
- Валидацию данных при создании
- Единообразную структуру для БД и Redis

---

## 🏗️ Иерархия DTO

```
ItemCoreData (базовый класс)
    ├─ WeaponData (оружие)
    ├─ ArmorData (броня)
    ├─ AccessoryData (аксессуары)
    ├─ ConsumableData (расходники)
    └─ ResourceData (ресурсы/валюта)

InventoryItemDTO (полиморфный wrapper)
    ├─ WeaponItemDTO
    ├─ ArmorItemDTO
    ├─ AccessoryItemDTO
    ├─ ConsumableItemDTO
    └─ ResourceItemDTO
```

---

## 📦 Вспомогательные модели

### ItemComponents
Хранит информацию о том, из чего собран предмет.

```python
class ItemComponents(BaseModel):
    base_id: str                    # ID базы (например, "longsword")
    material_id: str                # ID материала ("mat_iron_ingot")
    essence_id: list[str] | None    # ID эссенций для аффиксов
```

**Пример:**
```python
ItemComponents(
    base_id="longsword",
    material_id="mat_iron_ingot_tier_2",
    essence_id=["essence_vampirism", "essence_fire"]
)
```

---

### ItemDurability
Информация о прочности предмета.

```python
class ItemDurability(BaseModel):
    current: float    # Текущая прочность
    max: float        # Максимальная прочность
```

**Пример:**
```python
ItemDurability(current=80.0, max=100.0)
```

**Логика:**
- Прочность снижается при использовании
- При `current <= 0` предмет ломается (нужен ремонт)
- `max` может снижаться при ремонте (износ)

---

## 🎯 ItemCoreData (Базовый класс)

Содержит поля, общие для всех типов предметов.

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

### Поля

| Поле              | Тип                | Описание                                           |
|-------------------|--------------------|---------------------------------------------------|
| `name`            | `str`              | Название предмета (генерируется или задаётся)     |
| `description`     | `str`              | Описание (может генерироваться через LLM)         |
| `base_price`      | `int`              | Базовая цена (для продажи торговцу)               |
| `components`      | `ItemComponents?`  | Из чего сделан предмет (для разбора/крафта)       |
| `durability`      | `ItemDurability?`  | Прочность (для экипировки)                         |
| `narrative_tags`  | `list[str]`        | Теги для генерации описаний ("fiery", "ancient")  |
| `implicit_bonuses`| `dict[str, float]` | Встроенные бонусы (от базы/материала)             |
| `bonuses`         | `dict[str, float]` | Явные бонусы (от аффиксов/заточки)                |

### Разница между implicit_bonuses и bonuses

**implicit_bonuses** — встроенные свойства предмета (от материала или базы):
```python
implicit_bonuses = {
    "physical_damage_bonus": 0.05,  # +5% урона от железа
}
```

**bonuses** — магические свойства (от аффиксов):
```python
bonuses = {
    "physical_damage_bonus": 0.10,      # +10% от аффикса
    "trigger_vampirism": True,          # Триггер от аффикса
    "fire_resistance": 0.15             # +15% огнестойкости
}
```

**В бою:** Оба типа бонусов суммируются в StatsEngine.

---

## ⚔️ WeaponData (Оружие)

```python
class WeaponData(ItemCoreData):
    # Математика урона
    power: float
    spread: float = 0.1
    accuracy: float = 0.0
    
    # Механика боя
    crit_chance: float = 0.0
    parry_chance: float = 0.0
    evasion_penalty: float = 0.0
    
    # Триггеры
    triggers: list[str] = Field(default_factory=list)
    
    # Классификация
    grip: str = "1h"
    subtype: str
    related_skill: str | None = None
    valid_slots: list[str]
```

### Поля (специфичные для оружия)

| Поле              | Тип        | Описание                                           |
|-------------------|------------|---------------------------------------------------|
| `power`           | `float`    | Базовая сила оружия (заменяет damage_min/max)     |
| `spread`          | `float`    | Разброс урона (0.1 = ±10%)                         |
| `accuracy`        | `float`    | Базовая точность (может быть отрицательной)        |
| `crit_chance`     | `float`    | Шанс крита от оружия (%)                           |
| `parry_chance`    | `float`    | Шанс парирования (для фехтования)                  |
| `evasion_penalty` | `float`    | Штраф к уворотам (тяжёлое оружие)                  |
| `triggers`        | `list[str]`| Триггеры оружия ("trigger_bleed", ...)             |
| `grip`            | `str`      | "1h", "2h", "off_hand"                             |
| `subtype`         | `str`      | "sword", "axe", "bow", "dagger", ...               |
| `related_skill`   | `str?`     | Скилл, который прокачивается ("skill_swords")      |
| `valid_slots`     | `list[str]`| Слоты, куда можно надеть ("main_hand", ...)        |

### Расчёт урона

```python
min_damage = power * (1 - spread)
max_damage = power * (1 + spread)

# Пример: power=15.0, spread=0.2
min_damage = 15.0 * 0.8 = 12.0
max_damage = 15.0 * 1.2 = 18.0
```

### Примеры

#### Пример 1: Железный длинный меч (базовый)
```python
WeaponData(
    name="Железный длинный меч",
    description="Прочный клинок из закалённого железа.",
    base_price=150,
    
    components=ItemComponents(
        base_id="longsword",
        material_id="mat_iron_ingot_tier_1",
        essence_id=None
    ),
    
    durability=ItemDurability(current=100.0, max=100.0),
    
    narrative_tags=["blade", "versatile", "iron"],
    
    implicit_bonuses={},
    bonuses={},
    
    # Математика
    power=15.0,              # 10 (base) * 1.5 (tier_mult)
    spread=0.2,              # От базы longsword
    accuracy=0.0,
    
    # Механика
    crit_chance=0.0,
    parry_chance=0.0,
    evasion_penalty=0.0,
    
    # Триггеры
    triggers=["trigger_bleed"],
    
    # Классификация
    grip="1h",
    subtype="sword",
    related_skill="skill_swords",
    valid_slots=["main_hand", "off_hand"]
)
```

#### Пример 2: Мифический меч вампира (с аффиксами)
```python
WeaponData(
    name="Звёздный клинок вечности <Vampirism>",
    description="Древний меч, пульсирующий тёмной энергией.",
    base_price=5000,
    
    components=ItemComponents(
        base_id="longsword",
        material_id="mat_starmetal_ingot_tier_5",
        essence_id=["essence_vampirism"]
    ),
    
    durability=ItemDurability(current=500.0, max=500.0),
    
    narrative_tags=["blade", "vampiric", "mythic", "starmetal"],
    
    implicit_bonuses={
        "physical_damage_bonus": 0.15   # От материала
    },
    
    bonuses={
        "trigger_vampirism": True,       # От аффикса
        "hp_regen": 2.0                  # От аффикса
    },
    
    # Математика
    power=75.0,              # 10 * 7.5 (tier 5 mult)
    spread=0.2,
    accuracy=0.05,
    
    # Механика
    crit_chance=0.1,         # +10% от материала
    parry_chance=0.0,
    evasion_penalty=0.0,
    
    # Триггеры
    triggers=["trigger_bleed"],
    
    # Классификация
    grip="1h",
    subtype="sword",
    related_skill="skill_swords",
    valid_slots=["main_hand", "off_hand"]
)
```

#### Пример 3: Щит (= оружие без урона)
```python
WeaponData(
    name="Железный круглый щит",
    description="Прочный щит для блокирования ударов.",
    base_price=100,
    
    components=ItemComponents(
        base_id="shield_round",
        material_id="mat_iron_ingot_tier_1",
        essence_id=None
    ),
    
    durability=ItemDurability(current=150.0, max=150.0),
    
    narrative_tags=["shield", "defensive", "iron"],
    
    implicit_bonuses={},
    bonuses={},
    
    # Математика (нет урона!)
    power=0.0,               # Щиты не наносят урон
    spread=0.0,
    accuracy=0.0,
    
    # Механика (защита)
    crit_chance=0.0,
    parry_chance=0.3,        # 30% шанс блока
    evasion_penalty=-0.1,    # -10% к уворотам
    
    # Триггеров НЕТ (защита через скиллы)
    triggers=[],
    
    # Классификация
    grip="off_hand",         # Только в левой руке
    subtype="shield",
    related_skill="skill_shield",
    valid_slots=["off_hand"]
)
```

---

## 🛡️ ArmorData (Броня)

```python
class ArmorData(ItemCoreData):
    # Математика защиты
    power: float
    
    # Механика защиты
    block_chance: float = 0.0
    evasion_penalty: float = 0.0
    dodge_cap_mod: float = 0.0
    
    # Триггеров НЕТ
    triggers: list[str] = Field(default_factory=list)
    
    # Классификация
    subtype: str
    related_skill: str | None = None
    valid_slots: list[str]
```

### Поля (специфичные для брони)

| Поле              | Тип        | Описание                                           |
|-------------------|------------|---------------------------------------------------|
| `power`           | `float`    | Flat Damage Reduction (снижение урона)             |
| `block_chance`    | `float`    | Шанс блока (только щиты, здесь всегда 0)           |
| `evasion_penalty` | `float`    | Штраф к шансу уворота (тяжёлая броня)              |
| `dodge_cap_mod`   | `float`    | Модификатор капа уворота (-0.25 = -25% к капу)    |
| `triggers`        | `list[str]`| Всегда пустой (триггеры только у оружия)           |
| `subtype`         | `str`      | "heavy", "light", "shield"                         |
| `related_skill`   | `str?`     | "skill_heavy_armor", "skill_light_armor"           |
| `valid_slots`     | `list[str]`| "head_armor", "chest_armor", ...                   |

### Примеры

#### Пример 1: Железный шлем
```python
ArmorData(
    name="Железный шлем",
    description="Прочный шлем, защищающий голову.",
    base_price=80,
    
    components=ItemComponents(
        base_id="helmet_closed",
        material_id="mat_iron_ingot_tier_1",
        essence_id=None
    ),
    
    durability=ItemDurability(current=100.0, max=100.0),
    
    narrative_tags=["helmet", "heavy", "iron"],
    
    implicit_bonuses={},
    bonuses={},
    
    # Математика
    power=8.0,               # Снижение урона на 8
    
    # Механика
    block_chance=0.0,
    evasion_penalty=-0.05,   # -5% к уворотам
    dodge_cap_mod=0.0,
    
    # Триггеров нет
    triggers=[],
    
    # Классификация
    subtype="heavy",
    related_skill="skill_heavy_armor",
    valid_slots=["head_armor"]
)
```

#### Пример 2: Кожаная куртка (лёгкая броня)
```python
ArmorData(
    name="Дублёная кожаная куртка",
    description="Гибкая броня, не стесняющая движений.",
    base_price=60,
    
    components=ItemComponents(
        base_id="leather_jacket",
        material_id="mat_leather_tier_1",
        essence_id=None
    ),
    
    durability=ItemDurability(current=80.0, max=80.0),
    
    narrative_tags=["leather", "light", "agile"],
    
    implicit_bonuses={
        "dodge_chance": 0.05    # +5% к уворотам от лёгкой брони
    },
    bonuses={},
    
    # Математика
    power=3.0,               # Меньше защиты, чем у тяжёлой
    
    # Механика
    block_chance=0.0,
    evasion_penalty=0.0,     # Без штрафа
    dodge_cap_mod=0.0,
    
    # Триггеров нет
    triggers=[],
    
    # Классификация
    subtype="light",
    related_skill="skill_light_armor",
    valid_slots=["chest_armor"]
)
```

---

## 💍 AccessoryData (Аксессуары)

```python
class AccessoryData(ItemCoreData):
    triggers: list[str] = Field(default_factory=list)
    valid_slots: list[str]
```

### Особенности

- **Нет математики** (power, spread, accuracy) — только бонусы
- **Триггеры** — технически могут быть, но обычно пустые
- **Назначение** — давать чистые статы (HP, резисты, скорость)

### Примеры

#### Пример 1: Кольцо силы
```python
AccessoryData(
    name="Железное кольцо силы",
    description="Грубое кольцо, наделяющее носителя мощью.",
    base_price=50,
    
    components=None,
    durability=None,
    
    narrative_tags=["ring", "strength"],
    
    implicit_bonuses={},
    bonuses={
        "strength": 2.0,              # +2 к силе (flat)
        "physical_damage_bonus": 0.03 # +3% физ. урона
    },
    
    triggers=[],
    valid_slots=["ring_1", "ring_2"]
)
```

#### Пример 2: Амулет защиты
```python
AccessoryData(
    name="Амулет каменной кожи",
    description="Древний амулет, затвердевающий кожу носителя.",
    base_price=200,
    
    components=None,
    durability=None,
    
    narrative_tags=["amulet", "protection", "stone"],
    
    implicit_bonuses={},
    bonuses={
        "physical_resistance": 0.10,   # +10% физ. резиста
        "hp_max": 20.0                 # +20 HP
    },
    
    triggers=[],
    valid_slots=["amulet"]
)
```

---

## 🧪 ConsumableData (Расходники)

```python
class ConsumableData(ItemCoreData):
    restore_hp: int = 0
    restore_energy: int = 0
    effects: list[str] = Field(default_factory=list)
    cooldown_rounds: int = 0
    is_quick_slot_compatible: bool = False
```

### Поля

| Поле                       | Тип        | Описание                                    |
|----------------------------|------------|---------------------------------------------|
| `restore_hp`               | `int`      | Восстановление HP                           |
| `restore_energy`           | `int`      | Восстановление энергии                      |
| `effects`                  | `list[str]`| Эффекты (баффы/дебаффы) ("buff_strength")   |
| `cooldown_rounds`          | `int`      | Кулдаун в раундах                           |
| `is_quick_slot_compatible` | `bool`     | Можно ли положить на пояс                   |

### Примеры

#### Пример 1: Зелье здоровья
```python
ConsumableData(
    name="Малое зелье здоровья",
    description="Восстанавливает 50 HP.",
    base_price=20,
    
    components=None,
    durability=None,
    
    narrative_tags=["potion", "healing"],
    
    implicit_bonuses={},
    bonuses={},
    
    # Эффекты
    restore_hp=50,
    restore_energy=0,
    effects=[],
    cooldown_rounds=0,
    is_quick_slot_compatible=True
)
```

#### Пример 2: Эликсир силы
```python
ConsumableData(
    name="Эликсир силы",
    description="Даёт +5 к силе на 3 раунда.",
    base_price=50,
    
    components=None,
    durability=None,
    
    narrative_tags=["elixir", "strength"],
    
    implicit_bonuses={},
    bonuses={},
    
    # Эффекты
    restore_hp=0,
    restore_energy=0,
    effects=["buff_strength_5"],  # Бафф +5 силы
    cooldown_rounds=3,
    is_quick_slot_compatible=True
)
```

---

## 🪨 ResourceData (Ресурсы/Валюта)

```python
class ResourceData(ItemCoreData):
    pass  # Нет дополнительных полей
```

### Особенности

- **Нет прочности** (не изнашиваются)
- **Нет слотов** (не надеваются)
- **Только для крафта и торговли**

### Примеры

#### Пример 1: Железная руда
```python
ResourceData(
    name="Железная руда",
    description="Грубая руда, пригодная для плавки.",
    base_price=5,
    
    components=None,
    durability=None,
    
    narrative_tags=["ore", "iron"],
    
    implicit_bonuses={},
    bonuses={}
)
```

#### Пример 2: Кристалл тира 3
```python
ResourceData(
    name="Сияющий кристалл",
    description="Кристалл энергии Разлома 3-го уровня.",
    base_price=100,
    
    components=None,
    durability=None,
    
    narrative_tags=["currency", "crystal", "tier_3"],
    
    implicit_bonuses={},
    bonuses={}
)
```

---

## 🔗 InventoryItemDTO (Полиморфный wrapper)

Это обёртка, которая хранится в БД и содержит метаданные инвентаря.

```python
class BaseInventoryItemDTO(BaseModel):
    inventory_id: int
    character_id: int
    location: str                      # "inventory", "equipped", "wallet"
    subtype: str
    rarity: ItemRarity
    quantity: int = 1
    equipped_slot: str | None = None
    quick_slot_position: str | None = None

class WeaponItemDTO(BaseInventoryItemDTO):
    item_type: Literal[ItemType.WEAPON]
    data: WeaponData

class ArmorItemDTO(BaseInventoryItemDTO):
    item_type: Literal[ItemType.ARMOR]
    data: ArmorData

# ... и т.д.

# Полиморфный тип
InventoryItemDTO = Annotated[
    WeaponItemDTO | ArmorItemDTO | AccessoryItemDTO | ConsumableItemDTO | ResourceItemDTO,
    Field(discriminator="item_type")
]
```

### Пример (в БД)

```python
WeaponItemDTO(
    inventory_id=123,
    character_id=1,
    location="equipped",
    subtype="sword",
    rarity=ItemRarity.RARE,
    quantity=1,
    equipped_slot="main_hand",
    quick_slot_position=None,
    
    item_type=ItemType.WEAPON,
    data=WeaponData(...)  # ← Весь WeaponData вложен сюда
)
```

---

## ✅ Валидация полей

### Правила валидации (Pydantic автоматически проверяет)

```python
# power >= 0
WeaponData(power=-5.0)  # ❌ ValidationError

# spread от 0.0 до 1.0
WeaponData(spread=1.5)  # ⚠️ Нет ограничения (TODO: добавить validator)

# grip in ["1h", "2h", "off_hand"]
WeaponData(grip="3h")  # ⚠️ Нет ограничения (TODO: добавить Literal)

# triggers — только у WeaponData
ArmorData(triggers=["trigger_bleed"])  # ✅ Технически можно, но должно быть []
```

### TODO: Добавить валидаторы

```python
from pydantic import field_validator

class WeaponData(ItemCoreData):
    power: float
    spread: float = 0.1
    
    @field_validator('power')
    def power_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('power must be >= 0')
        return v
    
    @field_validator('spread')
    def spread_must_be_valid(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('spread must be between 0.0 and 1.0')
        return v
```

---

## 📚 Связанная документация

- **Система предметов:** [README.md](../../rpg_system/items/README.md)
- **Триггеры:** [weapon_triggers/README.md](./weapon_triggers/README.md)
- **Миграция на DTO:** [migration_to_dto.md](migration_to_dto.md)

---

**Последнее обновление:** Январь 2026  
**Статус:** Актуально (RBC v3.1)
