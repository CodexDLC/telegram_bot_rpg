# DESIGN DOCUMENT: MONSTER REGISTRY & ENCOUNTER SYSTEM

Version: 1.0 (Registry Model)

Status: Approved Concept

Target Module: apps/game_core/game_service/world/

---

## 1. Концепция: "Реестр и Поиск" (Registry & Lookup)

Мы отказываемся от динамической генерации математики "на лету" и от прямого копирования игроков.

Вместо этого используется Централизованный Реестр Шаблонов (Registry).

1. **Подземелья:** При генерации данжа скрипт берет конкретные шаблоны из Реестра.
    
2. **Открытый Мир:** При возникновении случайного боя (Random Encounter) система ищет подходящего монстра в Реестре по тегам текущей локации.
    
3. **Вариативность:** Один шаблон (`orc_grunt`) превращается в сотни уникальных описаний благодаря LLM, но его боевая математика остается предсказуемой.
    

---

## 2. Архитектура Данных

Данные хранятся в JSON-файлах, разбитых по Семействам.

Путь: apps/game_core/resources/game_data/monsters/families/

### Структура Шаблона (Template Schema)

Каждый монстр описывается следующими полями:

- **`template_id`**: Уникальный ключ (например, `orc_snow_hunter`).
    
- **`narrative_hint`**: Короткая фраза-якорь для LLM (например, _"pale orc with fur armor, ice spear"_).
    
- **`base_stats`**: Атрибуты до скалирования (Сила, Ловкость и т.д.).
    
- **`skills`**: Список ID способностей.
    
- **`allowed_tiers`**: Список уровней угрозы (0-7), на которых этот моб может появиться.
    
- **`environment_tags`**: Теги для поиска в открытом мире (Biome, Anchor, Special).
    

### Пример файла: `orcs.json`

JSON

```
{
  "family_id": "orc_clan",
  "default_tags": ["humanoid", "savage", "green_skin"],
  "templates": {
    "orc_grunt": {
      "narrative_hint": "primitive warrior, scarred skin, rusted axe",
      "base_stats": {
        "strength": 15,
        "agility": 8,
        "endurance": 12,
        "intelligence": 3
      },
      "skills": ["heavy_strike", "shout"],
      "allowed_tiers": [1, 2, 3],
      "environment_tags": ["forest", "wasteland", "ruins"]
    },
    "orc_snow_hunter": {
      "narrative_hint": "bulky orc, thick white fur, ice-infused spear",
      "base_stats": {
        "strength": 14,
        "agility": 12,
        "endurance": 14,
        "intelligence": 5
      },
      "skills": ["ice_spear", "camouflage"],
      "allowed_tiers": [2, 3, 4],
      "environment_tags": ["ice", "mountain", "cold_wind"]
    }
  }
}
```

---

## 3. Логика Скалирования (Tier Scaling)

Монстр получает финальные характеристики путем умножения базовых атрибутов на коэффициент Тира.

**Файл:** `apps/game_core/resources/game_data/monsters/_tiers.json`

|**Tier**|**Stat Multiplier**|**Role Description**|
|---|---|---|
|**0**|x0.5|Safe Zone / Tutorial|
|**1**|x1.0|Standard Baseline|
|**2**|x1.5|Hard|
|...|...|...|
|**5**|x5.0|Nightmare|

**Pipeline Расчета:**

1. `Raw Stats` = `Template.base_stats` * `Tier.multiplier`.
    
2. `Derived Stats` (HP, Dmg) = `ModifiersCalculatorService.calculate(Raw Stats)`.
    
3. Это гарантирует, что монстр использует ту же боевую математику, что и игрок.
    

---

## 4. Алгоритм "Поиска" (Encounter Logic)

Когда в Открытом Мире срабатывает триггер боя:

1. Сбор Контекста:
    
    Система получает данные о тайле игрока: Tier=2, Tags=[ice, mountain, north_anchor].
    
2. Фильтрация Реестра:
    
    EncounterService сканирует все JSON-файлы.
    
    - _Check 1:_ `allowed_tiers` содержит `2`?
        
    - _Check 2:_ Есть ли пересечение между `environment_tags` монстра и тегами тайла?
        
3. **Выбор:**
    
    - `orc_grunt`: (tags: forest) -> Нет совпадений.
        
    - `orc_snow_hunter`: (tags: ice) -> **Match!**
        
4. **Результат:** Спавнится `orc_snow_hunter` 2-го Тира.
    

---

## 5. Интеграция с LLM (Narrative Generation)

Итоговое описание монстра формируется динамически.

**Входные данные:**

- `Template Hint`: "pale orc with fur armor"
    
- `World Context`: "North Anchor, Tier 2, Ice Storm"
    

**Промпт:**

> "Сгенерируй имя и описание врага. Основа: [pale orc...]. Окружение: [Ice Storm...]. Монстр должен выглядеть органично для этого биома."

**Результат:**

> Имя: Клыкастый Охотник Стужи
> 
> Описание: Из снежной бури выходит массивная фигура. Это орк, но его кожа бледна как смерть, а доспехи сделаны из шкур полярных медведей. На его копье намерзли сосульки.

---

## 6. План Разработки (Roadmap)

### Phase 1: Data Structures

- [ ] Создать директорию `apps/game_core/resources/game_data/monsters/`.
    
- [ ] Создать `_tiers.json` (таблица множителей).
    
- [ ] Создать `families/orcs.json` (первый тестовый файл).
    

### Phase 2: Core Services

- [ ] **`MonsterRegistryService`**: Загрузка и кэширование JSON-файлов при старте.
    
- [ ] **`EncounterService`**: Логика поиска (`find_monster(tier, tags)`).
    

### Phase 3: Battle Integration

- [ ] **`MonsterFactory`**: Преобразование шаблона в `CombatSessionContainerDTO`.
    
- [ ] Подключение `ModifiersCalculator` для расчета HP/Dmg монстра.
    

### Phase 4: Content & Polish

- [ ] Интеграция с LLM для генерации описаний.
    
- [ ] Наполнение базы (Beasts, Undead, Humans).