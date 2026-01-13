# Inventory Formatting and UI

## 📋 Обзор

Описание компонента `InventoryFormatter`, отвечающего за подготовку данных инвентаря для отображения в клиенте (Telegram Bot UI).

---

## 🏗️ InventoryFormatter

**Назначение:** Преобразование внутренних структур данных (DTO) в формат, удобный для UI.

**Расположение:** `apps/game_core/modules/inventory/inventory/logic/inventory_formatter.py`

**Ответственность:**
- Группировка предметов (по типу, редкости)
- Сортировка (алфавит, цена, уровень)
- Фильтрация (оружие, броня, расходники)
- Генерация tooltip данных (детальное описание предмета)
- Подготовка статистики инвентаря (вес, слоты)

---

## 🎯 Основные методы

### 1. format_for_ui

**Назначение:** Главный метод форматирования для просмотра инвентаря.

**Сигнатура:**
```python
def format_for_ui(self, session: dict) -> InventoryViewDTO
```

**Параметры:**
- `session` (dict) — Redis Session инвентаря

**Возвращает:**
```python
InventoryViewDTO(
    equipped={...},       # Экипированные предметы
    backpack=[...],       # Рюкзак
    quick_slots=[...],    # Быстрые слоты
    stats={...}           # Статистика
)
```

**Логика:**
1. Извлечение данных из сессии
2. Форматирование каждой секции (equipped, backpack, quick_slots)
3. Расчёт статистики (вес, слоты)
4. Возврат унифицированного DTO

---

### 2. format_equipped

**Назначение:** Форматирование экипированных предметов.

**Сигнатура:**
```python
def format_equipped(self, equipped: dict) -> dict[str, ItemDTO | None]
```

**Пример вывода:**
```python
{
    "main_hand": WeaponDTO(
        id=123,
        name="Flaming Longsword",
        icon="⚔️",
        power=18,
        accuracy=85,
        durability=80
    ),
    "off_hand": ShieldDTO(
        id=124,
        name="Iron Shield",
        icon="🛡️",
        block_chance=30,
        durability=90
    ),
    "head": None,  # Пустой слот
    "chest": ArmorDTO(...),
    # ...
}
```

---

### 3. format_backpack

**Назначение:** Форматирование рюкзака с группировкой стакающихся предметов.

**Сигнатура:**
```python
def format_backpack(
    self,
    items: list[dict],
    group_by: str | None = None,
    sort_by: str = "name",
    filter_type: str | None = None
) -> list[InventoryItemDTO]
```

**Параметры:**
- `items` (list[dict]) — Список предметов из сессии
- `group_by` (str | None) — Группировка ("type", "rarity", None)
- `sort_by` (str) — Сортировка ("name", "value", "rarity", "level")
- `filter_type` (str | None) — Фильтр ("weapon", "armor", "consumable", None)

**Пример вывода (без группировки):**
```python
[
    InventoryItemDTO(
        id=1,
        name="Health Potion",
        icon="🧪",
        type="consumable",
        quantity=5,
        value=10
    ),
    InventoryItemDTO(
        id=2,
        name="Iron Sword",
        icon="⚔️",
        type="weapon",
        quantity=1,
        value=50
    ),
    # ...
]
```

**Пример вывода (с группировкой по типу):**
```python
{
    "weapons": [
        InventoryItemDTO(id=2, name="Iron Sword", ...),
        InventoryItemDTO(id=5, name="Steel Axe", ...)
    ],
    "armor": [
        InventoryItemDTO(id=3, name="Leather Helmet", ...),
        InventoryItemDTO(id=4, name="Chain Vest", ...)
    ],
    "consumables": [
        InventoryItemDTO(id=1, name="Health Potion", quantity=5, ...),
        InventoryItemDTO(id=6, name="Mana Potion", quantity=3, ...)
    ]
}
```

---

### 4. format_quick_slots

**Назначение:** Форматирование быстрых слотов с учётом пустых позиций.

**Сигнатура:**
```python
def format_quick_slots(self, quick_slots: list[dict | None]) -> list[ConsumableDTO | None]
```

**Пример вывода:**
```python
[
    ConsumableDTO(id=1, name="Health Potion", icon="🧪", quantity=5),
    None,  # Пустой слот
    ConsumableDTO(id=2, name="Scroll of Fireball", icon="📜", charges=1),
    None,
    # ...
]
```

---

### 5. calculate_stats

**Назначение:** Расчёт статистики инвентаря (вес, слоты, ценность).

**Сигнатура:**
```python
def calculate_stats(self, session: dict) -> InventoryStatsDTO
```

**Возвращает:**
```python
InventoryStatsDTO(
    total_weight=45.5,       # Текущий вес
    max_weight=100.0,        # Макс. вес (зависит от Strength)
    weight_percent=45.5,     # Процент заполнения
    slots_used=12,           # Занятые слоты
    max_slots=50,            # Макс. слоты (зависит от сумки)
    slots_percent=24.0,      # Процент заполнения
    total_value=1250,        # Общая ценность всех предметов
    is_overweight=False      # Флаг перегруза
)
```

**Логика:**
1. Подсчёт общего веса (equipped + backpack)
2. Получение макс. веса через атрибуты персонажа
3. Подсчёт занятых слотов
4. Расчёт ценности всех предметов

---

### 6. generate_tooltip

**Назначение:** Генерация детального описания предмета для tooltip.

**Сигнатура:**
```python
def generate_tooltip(self, item: ItemDTO, char_stats: dict | None = None) -> str
```

**Параметры:**
- `item` (ItemDTO) — Предмет
- `char_stats` (dict | None) — Статы персонажа (для проверки требований)

**Пример вывода (оружие):**
```
⚔️ Flaming Longsword of the Bear
━━━━━━━━━━━━━━━━━━━━━━━
🔸 Rare Weapon (Sword)

📊 Stats:
  • Damage: 15-20 (Physical)
  • Accuracy: 85%
  • Crit Chance: 10%
  • Attack Speed: Normal

✨ Bonuses:
  • +5 Fire Damage
  • +10 Strength
  • +15% Fire Resistance

⚙️ Requirements:
  • Strength: 12 ✅
  • Level: 5 ✅

🔧 Durability: 80/100
💰 Value: 350 gold
⚖️ Weight: 4.5 kg
```

**Пример вывода (зелье):**
```
🧪 Greater Health Potion
━━━━━━━━━━━━━━━━━━━━━━━
🟢 Common Consumable

💚 Effects:
  • Restores 100 HP instantly
  • +10 HP/sec for 5 seconds

📦 Quantity: 3
💰 Value: 50 gold (each)
⚖️ Weight: 0.2 kg (each)
```

**Логика:**
1. Название + рарность + тип
2. Статы (для оружия/брони)
3. Бонусы (от аффиксов)
4. Требования (с проверкой выполнения ✅/❌)
5. Прочность (для экипировки)
6. Ценность и вес

---

## 🎨 UI Layout Examples

### Просмотр инвентаря (Telegram)

```
👤 Character: Aetheron
━━━━━━━━━━━━━━━━━━━━━━━

⚔️ EQUIPPED:
  Main Hand: Flaming Longsword [⚙️ 80/100]
  Off Hand: Iron Shield [⚙️ 90/100]
  Head: —
  Chest: Leather Vest [⚙️ 95/100]
  Legs: Chain Leggings [⚙️ 85/100]

🎒 BACKPACK (12/50):
  [Filter: All ▼] [Sort: Name ▼]

  🗡️ Weapons (2):
    • Steel Dagger ⚖️ 1.5kg 💰 30g
    • Wooden Bow ⚖️ 2.0kg 💰 40g

  🛡️ Armor (3):
    • Iron Helmet ⚖️ 3.0kg 💰 50g
    • Leather Gloves ⚖️ 0.5kg 💰 15g
    • Cloth Boots ⚖️ 0.8kg 💰 10g

  🧪 Consumables (7):
    • Health Potion x5 ⚖️ 1.0kg 💰 50g
    • Mana Potion x2 ⚖️ 0.4kg 💰 30g

⚡ QUICK SLOTS:
  [1] Health Potion 🧪 x5
  [2] —
  [3] Scroll of Fireball 📜 x1

📊 STATS:
  ⚖️ Weight: 45.5 / 100.0 kg (45%)
  📦 Slots: 12 / 50 (24%)
  💰 Total Value: 1,250 gold

[⚙️ Equip] [🗑️ Drop] [🔍 Details] [🔄 Sort]
```

---

## 🔧 Группировка и сортировка

### Группировка

**По типу (group_by="type"):**
```python
{
    "weapons": [...],
    "armor": [...],
    "consumables": [...],
    "materials": [...],
    "quest_items": [...]
}
```

**По редкости (group_by="rarity"):**
```python
{
    "legendary": [...],
    "epic": [...],
    "rare": [...],
    "uncommon": [...],
    "common": [...]
}
```

### Сортировка

**По имени (sort_by="name"):**
```python
# Алфавитный порядок (А-Я, A-Z)
["Axe", "Bow", "Dagger", "Sword"]
```

**По ценности (sort_by="value"):**
```python
# От дорогих к дешёвым
[350, 100, 50, 10]
```

**По редкости (sort_by="rarity"):**
```python
# Legendary → Epic → Rare → Uncommon → Common
```

**По уровню (sort_by="level"):**
```python
# От высокого к низкому
[15, 10, 5, 1]
```

### Фильтрация

**По типу (filter_type="weapon"):**
```python
# Показать только оружие
[WeaponDTO(...), WeaponDTO(...), ...]
```

**По редкости (filter_rarity="rare"):**
```python
# Показать только Rare+ предметы
[RareItem(...), EpicItem(...), LegendaryItem(...)]
```

**По экипируемости (filter_equippable=True):**
```python
# Показать только то, что можно экипировать (соответствует требованиям)
```

---

## 🎯 Продвинутые фичи

### 1. Стакинг предметов

Одинаковые предметы (с одинаковым `base_item_id` и аффиксами) объединяются:

```python
# До стакинга:
[
    {"id": 1, "name": "Health Potion", "quantity": 1},
    {"id": 2, "name": "Health Potion", "quantity": 1},
    {"id": 3, "name": "Health Potion", "quantity": 3}
]

# После стакинга:
[
    {"id": 1, "name": "Health Potion", "quantity": 5}
]
```

### 2. Highlight New Items

Предметы, добавленные менее 5 минут назад, помечаются:

```python
InventoryItemDTO(
    id=123,
    name="Steel Sword",
    is_new=True,  # Показать бейдж "NEW"
    added_at=1704067200
)
```

### 3. Comparison Tooltip

Сравнение экипируемого предмета с текущим в слоте:

```
⚔️ Steel Sword vs. Iron Sword
━━━━━━━━━━━━━━━━━━━━━━━
Damage: 20-25 (+5) ⬆️
Accuracy: 80% (-5%) ⬇️
Crit Chance: 8% (+3%) ⬆️
Weight: 5.0 kg (+1.5 kg) ⬇️

Overall: ⬆️ UPGRADE
```

### 4. Search

Фильтрация по подстроке в названии:

```python
def search(self, items: list[ItemDTO], query: str) -> list[ItemDTO]:
    return [item for item in items if query.lower() in item.name.lower()]

# Пример:
search(backpack, "sword")  # ["Longsword", "Shortsword", "Greatsword"]
```

---

## 🎨 Стилизация (Telegram)

### Иконки по типам предметов

```python
ITEM_ICONS = {
    "weapon_sword": "⚔️",
    "weapon_axe": "🪓",
    "weapon_bow": "🏹",
    "weapon_staff": "🪄",
    "armor_helmet": "🪖",
    "armor_chest": "🛡️",
    "armor_legs": "👖",
    "consumable_potion": "🧪",
    "consumable_scroll": "📜",
    "material": "🔩",
    "quest_item": "📦"
}
```

### Цветовые метки редкости

```python
RARITY_EMOJI = {
    "common": "⚪",
    "uncommon": "🟢",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🟠"
}

# Пример:
"🔵 Steel Longsword"  # Rare
```

---

## 📊 Производительность

### Оптимизация группировки

Для больших инвентарей (>100 предметов) используется индексация:

```python
def group_by_type_optimized(items: list[ItemDTO]) -> dict:
    grouped = defaultdict(list)
    for item in items:
        grouped[item.type].append(item)
    return dict(grouped)

# O(n) вместо O(n²)
```

### Кэширование tooltip'ов

Tooltip'ы кэшируются на время сессии:

```python
_tooltip_cache: dict[int, str] = {}  # {item_id: tooltip}

def generate_tooltip_cached(self, item: ItemDTO) -> str:
    if item.id in self._tooltip_cache:
        return self._tooltip_cache[item.id]

    tooltip = self._generate_tooltip_internal(item)
    self._tooltip_cache[item.id] = tooltip
    return tooltip
```

---

## 🎯 Ключевые принципы

1. **Separation of Concerns**
   - Formatter не изменяет данные, только форматирует

2. **UI-Agnostic**
   - Возвращает DTO, а не готовый HTML/Telegram Markup
   - UI-слой (bot handlers) решает как отображать

3. **Flexibility**
   - Настраиваемая группировка, сортировка, фильтрация
   - Легко добавить новые режимы отображения

4. **Performance**
   - Кэширование дорогих операций
   - Оптимизация алгоритмов для больших списков

---

## 📚 Связанная документация

- **Inventory Architecture:** [./inventory_architecture.md](./inventory_architecture.md)
- **Gateway API:** [./gateway.md](./gateway.md)
- **Session Management:** [./session_management.md](./session_management.md)

---

**Последнее обновление:** Январь 2026
**Статус:** Архитектурная фаза
