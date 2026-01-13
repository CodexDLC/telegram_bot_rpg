# Item Creation Pipeline (Конвейер создания предметов)

## 📋 Обзор

Этот документ описывает полный процесс создания игрового предмета — от выбора базы до финальной записи в БД.

**Ключевые компоненты:**
1. **ItemAssembler** — фабрика сборки предметов
2. **ItemDistributionService** — сервис выдачи лута
3. **LootService** — правила дропа
4. **Gemini LLM** — генерация описаний (опционально)

---

## 🏗️ Архитектура системы

```
Game Event (Убийство моба / Крафт)
    ↓
LootService.roll_combat_loot()
    ├─ Определяет: дропать или нет?
    ├─ Определяет: какой тир?
    └─ Вызывает ItemDistributionService
         ↓
ItemDistributionService.prepare_random_loot()
    ├─ Выбирает случайную базу (get_random_base)
    └─ Вызывает ItemAssembler
         ↓
ItemAssembler.assemble_equipment()
    ├─ Загружает BaseItemDTO
    ├─ Загружает MaterialDTO
    ├─ Считает power, durability
    ├─ Применяет аффиксы (_apply_bundles)
    ├─ Генерирует имя (пока без LLM)
    └─ Возвращает dict payload
         ↓
ItemDistributionService.prepare_random_loot() (продолжение)
    ├─ Создаёт запись в БД (inventory_repo.create_item)
    ├─ location = "generated_loot" (у SYSTEM)
    └─ Возвращает InventoryItemDTO
         ↓
ItemDistributionService.issue_item_to_player()
    └─ Передаёт предмет игроку (меняет owner_id)
```

---

## 🔧 Компонент 1: ItemAssembler

### Назначение
Превращает набор ID (base, material, bundle) в готовый JSON payload предмета.

### Файл
`apps/game_core/modules/inventory/Item/item_assembler.py`

### Метод: assemble_equipment()

```python
@staticmethod
def assemble_equipment(
    base_id: str,
    target_tier: int,
    bundle_id: str | None = None,
) -> tuple[str, str, str, dict[str, Any]]:
```

**Входные данные:**
- `base_id` — ID базы ("longsword", "helmet_closed")
- `target_tier` — уровень сложности (0-7)
- `bundle_id` — ID аффикса (опционально)

**Возвращает:**
- `item_type` — "weapon", "armor", "accessory"
- `base_id` — ID базы (для components)
- `rarity_enum` — "rare", "epic", ...
- `data_payload` — dict с полями предмета

---

### Шаги сборки

#### Шаг 1: Загрузка базы

```python
base_data = get_base_by_id(base_id)
# BaseItemDTO {
#     id: "longsword",
#     name_ru: "Длинный меч",
#     base_power: 10,
#     damage_spread: 0.2,
#     triggers: ["trigger_bleed"],
#     allowed_materials: ["ingots"]
# }
```

#### Шаг 2: Загрузка материала

```python
material_cat = base_data["allowed_materials"][0]  # "ingots"
material_data = get_material_for_tier(material_cat, target_tier)
# MaterialDTO {
#     id: "mat_iron_ingot_tier_1",
#     name_ru: "Железный слиток",
#     tier_mult: 1.5,
#     slots: 2
# }
```

#### Шаг 3: Расчёт характеристик

```python
# Множитель с разбросом
mult = material_data["tier_mult"]  # 1.5
variance = random.uniform(0.9, 1.1)  # ±10%
final_mult = mult * variance  # 1.35 - 1.65

# Сила предмета
final_power = int(base_data["base_power"] * final_mult)
# 10 * 1.5 = 15

# Прочность
max_durability = int(base_data["base_durability"] * mult)
# 100 * 1.5 = 150
```

#### Шаг 4: Создание базового payload

```python
data_payload = {
    "name": f"{material_data['name_ru']} {base_data['name_ru'].split()[-1]}",
    # "Железный меч"
    
    "description": f"Создано из {material_data['name_ru']}.",
    
    "base_price": int(10 * final_mult * (target_tier + 1)),
    
    "narrative_tags": base_data["narrative_tags"] + material_data["narrative_tags"],
    # ["blade", "versatile"] + ["iron", "durable"]
    
    "components": {
        "base_id": base_id,
        "material_id": material_data["id"]
    },
    
    "durability": {
        "current": max_durability,
        "max": max_durability
    },
    
    "valid_slots": [base_data["slot"]],
    
    "bonuses": base_data.get("implicit_bonuses", {}).copy()
}
```

#### Шаг 5: Добавление полей по типу

**Для оружия (ItemType.WEAPON):**
```python
if item_type == ItemType.WEAPON:
    spread = base_data.get("damage_spread", 0.2)
    dmg_min = int(final_power * (1 - spread))
    dmg_max = int(final_power * (1 + spread))
    
    data_payload["damage_min"] = max(1, dmg_min)  # 12
    data_payload["damage_max"] = max(2, dmg_max)  # 18
```

**⚠️ ПРОБЛЕМА:** Это старая схема! Нужно заменить на:
```python
data_payload["power"] = final_power  # 15.0
data_payload["spread"] = spread      # 0.2
data_payload["accuracy"] = 0.0
data_payload["triggers"] = base_data.get("triggers", [])
```

**Для брони (ItemType.ARMOR):**
```python
elif item_type == ItemType.ARMOR:
    data_payload["protection"] = max(1, final_power)
```

**⚠️ ПРОБЛЕМА:** Нужно заменить на:
```python
data_payload["power"] = final_power  # Flat reduction
```

#### Шаг 6: Применение аффиксов

```python
ItemAssembler._apply_bundles(data_payload, material_data, bundle_id)
```

Этот метод:
1. Проверяет доступные слоты материала
2. Выбирает бандлы (primary + random fills)
3. Добавляет эффекты в `bonuses`
4. Добавляет суффикс к имени

**Пример:**
```python
# До
data_payload["name"] = "Железный меч"
data_payload["bonuses"] = {}

# После (с аффиксом vampirism)
data_payload["name"] = "Железный меч <Vampirism>"
data_payload["bonuses"] = {
    "trigger_vampirism": True,
    "physical_damage_bonus": 0.05
}
data_payload["components"]["essence_id"] = ["essence_vampirism"]
```

---

### Алгоритм применения аффиксов (_apply_bundles)

```python
available_slots = material_data.get("slots", 0)  # 2 слота
remaining_slots = available_slots

# 1. Применяем primary bundle (если указан)
if primary_bundle_id:
    bundle = BUNDLES_DB.get(primary_bundle_id)
    if bundle and bundle["cost_slots"] <= remaining_slots:
        bundles_to_apply.append(bundle)
        remaining_slots -= bundle["cost_slots"]

# 2. Заполняем оставшиеся слоты случайными бандлами
while remaining_slots > 0:
    possible = [b for b in BUNDLES_DB.values() if b["cost_slots"] <= remaining_slots]
    if not possible:
        break
    
    chosen = random.choice(possible)
    bundles_to_apply.append(chosen)
    remaining_slots -= chosen["cost_slots"]

# 3. Применяем эффекты
for bundle in bundles_to_apply:
    for effect_key in bundle["effects"]:
        effect = EFFECTS_DB.get(effect_key)
        
        final_value = effect["base_value"] * material_data["tier_mult"]
        target_field = effect["target_field"]
        
        current_bonus = data_payload["bonuses"].get(target_field, 0.0)
        data_payload["bonuses"][target_field] = current_bonus + final_value
```

**Пример:**
```python
# Bundle: "vampirism" (cost 2 slots)
# Effects: ["vampirism", "hp_regen"]

# Effect "vampirism"
{
    "target_field": "vampiric_power",
    "base_value": 0.02,
    "is_percentage": True
}

# Итог в bonuses
bonuses["vampiric_power"] = 0.02 * 1.5 = 0.03  # 3% вампиризма
```

---

## 🎲 Компонент 2: LootService

### Назначение
Определяет, выпадает ли лут и какого качества.

### Файл
`apps/game_core/modules/inventory/Item/loot_service.py`

### Метод: roll_combat_loot()

```python
async def roll_combat_loot(
    self, 
    mob_tier: int, 
    luck_modifier: float = 1.0
) -> InventoryItemDTO | None:
```

**Входные данные:**
- `mob_tier` — уровень монстра (0-7)
- `luck_modifier` — множитель удачи игрока (1.0 = норма)

**Возвращает:**
- `InventoryItemDTO` или `None` (если не повезло)

### Алгоритм

#### 1. Ролл на факт дропа

```python
BASE_DROP_CHANCE = 0.3  # 30%
final_chance = min(1.0, BASE_DROP_CHANCE * luck_modifier)

roll = random.random()
if roll > final_chance:
    return None  # Не повезло
```

#### 2. Определение тира предмета

```python
tier_roll = random.random()
jackpot_chance = 0.05 * luck_modifier

if tier_roll < 0.15:
    item_tier = max(0, mob_tier - 1)  # 15% — хлам
elif tier_roll > (1.0 - jackpot_chance):
    item_tier = mob_tier + 1          # 5% — джекпот
else:
    item_tier = mob_tier              # 80% — норма
```

**Пример:**
- Моб тир 3
- Шанс хлама: 15% → тир 2
- Шанс нормы: 80% → тир 3
- Шанс джекпота: 5% → тир 4

#### 3. Делегирование создания

```python
loot_item = await self.distribution_service.prepare_random_loot(tier=item_tier)
return loot_item
```

---

## 🎁 Компонент 3: ItemDistributionService

### Назначение
Создаёт предмет и сохраняет его в БД у SYSTEM, готовый к передаче игроку.

### Файл
`apps/game_core/modules/inventory/Item/item_distribution_service.py`

### Метод: prepare_random_loot()

```python
async def prepare_random_loot(
    self, 
    tier: int, 
    category_filter: str | None = None
) -> InventoryItemDTO | None:
```

**Входные данные:**
- `tier` — тир предмета (0-7)
- `category_filter` — фильтр категории ("weapon", "armor") или None

**Возвращает:**
- `InventoryItemDTO` (с БД ID) или `None` при ошибке

### Алгоритм

#### 1. Выбор случайной базы

```python
random_base = get_random_base(category_filter)
base_id = random_base["id"]  # "longsword"
```

#### 2. Сборка через ItemAssembler

```python
item_type, item_subtype, rarity_enum, item_data = ItemAssembler.assemble_equipment(
    base_id=base_id,
    target_tier=tier
)
```

#### 3. Создание записи в БД

```python
item_id = await self.inventory_repo.create_item(
    character_id=settings.system_char_id,  # SYSTEM (не игрок!)
    item_type=item_type,
    subtype=item_subtype,
    rarity=rarity_enum,
    item_data=item_data,
    location="generated_loot"  # Буферная зона
)
```

**⚠️ Важно:** Предмет создаётся у SYSTEM, а не у игрока!

#### 4. Возврат DTO

```python
return await self.inventory_repo.get_item_by_id(item_id)
```

---

### Метод: issue_item_to_player()

```python
async def issue_item_to_player(
    self, 
    item_id: int, 
    player_char_id: int
) -> bool:
```

**Назначение:** Финализация — передача предмета игроку.

**Алгоритм:**
```python
# 1. Проверка, что предмет принадлежит SYSTEM
item = await self.inventory_repo.get_item_by_id(item_id)
if item.character_id != settings.system_char_id:
    return False

# 2. Передача игроку
success = await self.inventory_repo.transfer_item(
    inventory_id=item_id,
    new_owner_id=player_char_id,
    new_location="inventory"
)

return success
```

---

## 🤖 Компонент 4: LLM Integration (Gemini)

### Текущий статус
⚠️ **Не реализовано полностью.** ItemAssembler генерирует базовое имя без LLM.

### Планируемая интеграция

#### Режим генерации: item_description

```python
# mode_preset.py
"item_description": {
    "system_instruction": """
    You are a creative writer for a dark fantasy RPG.
    Write a short, atmospheric description for an item based on its name and tags.
    The description should be 2-3 sentences long.
    Format: {"description": "your text"}.
    Return ONLY the JSON object.
    """,
    "temperature": 0.7,
    "max_tokens": 256,
    "model_alias": "fast"
}
```

#### Использование

```python
# После создания базового payload
item_name = data_payload["name"]  # "Железный меч <Vampirism>"
narrative_tags = data_payload["narrative_tags"]  # ["blade", "vampiric", "iron"]

# Формируем промпт
prompt = f"Item: {item_name}\nTags: {', '.join(narrative_tags)}"

# Вызываем LLM
response = await gemini_answer(mode="item_description", user_text=prompt)

# Парсим JSON
llm_data = json.loads(response)
data_payload["description"] = llm_data["description"]
```

**Пример результата:**
```json
{
    "description": "Тёмный клинок, пульсирующий жаждой крови. Каждый удар этого меча питает своего владельца жизненной силой врага. Железо, пропитанное проклятием."
}
```

### Варианты реализации

#### Option A: Синхронно при крафте
```python
# ItemAssembler.assemble_equipment()
if use_llm:
    description = await generate_description_llm(data_payload)
    data_payload["description"] = description
else:
    data_payload["description"] = f"Создано из {material_data['name_ru']}."
```

**Плюсы:** Предмет сразу готов с описанием  
**Минусы:** Медленный крафт (ждём LLM)

#### Option B: Асинхронно (фоновая задача)
```python
# ItemDistributionService.prepare_random_loot()
item_id = await self.inventory_repo.create_item(...)

# Запускаем фоновую задачу
await enqueue_llm_description_task(item_id)

return item
```

**Плюсы:** Быстрый дроп  
**Минусы:** Игрок видит временное описание

#### Option C: Кэширование шаблонов
```python
# Генерируем описания для типовых комбинаций заранее
CACHED_DESCRIPTIONS = {
    ("longsword", "iron", "tier_1"): "Прочный железный клинок...",
    ("longsword", "iron", "tier_1", "vampirism"): "Проклятый меч...",
}
```

**Плюсы:** Мгновенный дроп  
**Минусы:** Ограниченное разнообразие

---

## 📊 Полный пример: Дроп из моба

### Входные данные
```python
mob_tier = 3
player_luck = 1.2  # +20% удачи
```

### Шаг 1: LootService.roll_combat_loot()

```python
# Ролл на дроп
BASE_DROP_CHANCE = 0.3
final_chance = 0.3 * 1.2 = 0.36  # 36%
roll = 0.25  # Повезло!

# Определение тира
tier_roll = 0.5  # Попали в 80% (норма)
item_tier = 3
```

### Шаг 2: ItemDistributionService.prepare_random_loot()

```python
# Выбор базы
random_base = get_random_base(None)
base_id = "longsword"
```

### Шаг 3: ItemAssembler.assemble_equipment()

```python
# Загрузка данных
base_data = BaseItemDTO(
    id="longsword",
    base_power=10,
    damage_spread=0.2,
    triggers=["trigger_bleed"],
    allowed_materials=["ingots"]
)

material_data = MaterialDTO(
    id="mat_steel_ingot_tier_3",
    name_ru="Стальной слиток",
    tier_mult=2.2,
    slots=3
)

# Расчёт
final_power = 10 * 2.2 * 1.05 = 23  # +5% variance
max_durability = 100 * 2.2 = 220

# Payload
data_payload = {
    "name": "Стальной меч",
    "description": "Создано из Стального слитка.",
    "base_price": 330,
    "components": {
        "base_id": "longsword",
        "material_id": "mat_steel_ingot_tier_3"
    },
    "durability": {"current": 220, "max": 220},
    "damage_min": 18,  # ⚠️ Старая схема
    "damage_max": 27,
    "bonuses": {}
}

# Аффиксы (3 слота)
# Random: "fire" (2 slots) + "sharpness" (1 slot)
data_payload["name"] = "Стальной меч <Fire> <Sharpness>"
data_payload["bonuses"] = {
    "fire_damage_bonus": 0.11,      # 0.05 * 2.2
    "physical_damage_bonus": 0.055  # 0.025 * 2.2
}
data_payload["components"]["essence_id"] = ["essence_fire", "essence_sharpness"]
```

### Шаг 4: Создание в БД

```python
item_id = 12345
location = "generated_loot"
character_id = 0  # SYSTEM
```

### Шаг 5: Передача игроку

```python
await ItemDistributionService.issue_item_to_player(
    item_id=12345,
    player_char_id=1
)

# Теперь предмет у игрока в инвентаре
```

---

## 🚧 Известные проблемы

### 1. ItemAssembler возвращает старые поля
**Проблема:** `damage_min`, `damage_max`, `protection` вместо `power`, `spread`.

**Решение:** Переписать под новые DTO.

**Файл:** `item_assembler.py`, строки 89-96

### 2. Триггеры не копируются из базы
**Проблема:** `base_data["triggers"]` не добавляются в `data_payload`.

**Решение:**
```python
if item_type == ItemType.WEAPON:
    data_payload["triggers"] = base_data.get("triggers", [])
```

### 3. Аффиксы не могут добавлять триггеры
**Проблема:** `_apply_bundles` работает только с `bonuses`, но не с `triggers`.

**Решение:**
```python
# Если аффикс даёт триггер
if effect["type"] == "trigger":
    data_payload["bonuses"][f"trigger_{effect['id']}"] = True
```

### 4. LLM интеграция не реализована
**Проблема:** Описания генерируются шаблонно.

**Решение:** Добавить вызов `gemini_answer()` в `ItemAssembler`.

---

## 📚 Связанная документация

- **DTO справочник:** [01_item_dto_reference.md](./01_item_dto_reference.md)
- **Система предметов:** [README.md](../../rpg_system/items/README.md)
- **Аффиксы:** `/apps/game_core/resources/game_data/items/affix_config.py`
- **LLM сервис:** `/apps/common/services/gemini_service/`

---

**Последнее обновление:** Январь 2026  
**Статус:** Требуется рефакторинг ItemAssembler под RBC v3.1