# DESIGN DOCUMENT: MONSTER REGISTRY & ENCOUNTER SYSTEM

Version: 1.1 (Python-based Concept)

Status: Concept

Target Module: `apps/game_core/game_service/world/`

---

## 1. Концепция: "Реестр и Поиск" (Registry & Lookup)

Мы отказываемся от динамической генерации "на лету". Вместо этого используется Централизованный Реестр Шаблонов.

1.  **Подземелья:** Скрипт берет конкретные шаблоны из Реестра.
2.  **Открытый Мир:** При случайном бое система ищет подходящего монстра в Реестре по тегам локации.
3.  **Вариативность:** Один шаблон (`orc_grunt`) превращается в сотни уникальных описаний благодаря LLM, а его боевая математика остается предсказуемой, но может быть модифицирована **Аффиксами**.

---

## 2. Архитектура Данных

Данные хранятся в **Python-файлах** с использованием `TypedDict` для скорости и строгой типизации.

Путь: `apps/game_core/resources/game_data/monsters/`

### Структура Шаблона (Template Schema)

Каждый монстр описывается в `families/*.py`:

-   **`template_id`**: Уникальный ключ (например, `orc_snow_hunter`).
-   **`narrative_hint`**: Якорь для LLM (_"pale orc with fur armor, ice spear"_).
-   **`base_stats`**: Атрибуты до скалирования.
-   **`skills`**: Список ID способностей.
-   **`allowed_tiers`**: Список уровней угрозы (0-7).
-   **`environment_tags`**: Теги для поиска (Biome, Anchor, Special).

### Пример файла: `families/orcs.py`

```python
ORCS_FAMILY: MonsterFamily = {
    "family_id": "orc_clan",
    "default_tags": ["humanoid", "savage"],
    "templates": {
        "orc_grunt": {
            "narrative_hint": "primitive warrior, rusted axe",
            "base_stats": {"strength": 15, ...},
            "skills": ["heavy_strike"],
            "allowed_tiers": [1, 2, 3],
            "environment_tags": ["forest", "wasteland"],
        },
    },
}
```

---

## 3. Логика Скалирования (Tier Scaling)

Монстр получает финальные характеристики путем умножения базовых атрибутов на коэффициент Тира.

**Файл:** `_tiers.py`

```python
TIER_MULTIPLIERS: dict[int, TierData] = {
    1: {"stat_multiplier": 1.0, ...},
    2: {"stat_multiplier": 1.5, ...},
}
```

**Pipeline Расчета:**

1.  `Raw Stats` = `Template.base_stats` * `Tier.multiplier`.
2.  `Derived Stats` (HP, Dmg) = `ModifiersCalculatorService.calculate(Raw Stats)`.

---

## 4. Динамические Аффиксы (Affixes)

Чтобы добавить вариативности, на монстра может быть наложен **стихийный аффикс** в зависимости от тегов локации.

**Файл:** `_affixes.py`

```python
MONSTER_AFFIXES: dict[str, MonsterAffix] = {
    "ice": {
        "visual_prefix": "Ice-Infused",
        "added_stats": {"water_resistance": 0.5, ...},
        "inject_skills": ["chilling_touch"],
    },
}
```

**Pipeline с Аффиксом:**

1.  `Raw Stats` = (`Template.base_stats` + `Affix.added_stats`) * `Tier.multiplier`.
2.  `Final Skills` = `Template.skills` + `Affix.inject_skills`.
3.  `Final Hint` = `Affix.visual_prefix` + `Template.narrative_hint`.

---

## 5. Алгоритм "Поиска" (Encounter Logic)

1.  **Контекст:** Система получает данные тайла: `Tier=2`, `Tags={"ice", "mountain"}`.
2.  **Поиск Монстра:** `EncounterService` вызывает `find_monsters_by_tags(tier=2, tags={"ice", "mountain"})`.
    -   `orc_grunt`: (tags: forest) -> Нет совпадений.
    -   `orc_snow_hunter`: (tags: ice) -> **Match!**
3.  **Поиск Аффикса:** Система видит тег `ice` и находит соответствующий аффикс в `MONSTER_AFFIXES`.
4.  **Сборка:** `MonsterFactory` собирает `orc_snow_hunter`, применяя на него аффикс `ice` и множитель `Tier 2`.
5.  **Результат:** Спавнится "Ice-Infused Orc Snow Hunter" 2-го Тира.

---

## 6. План Разработки (Roadmap)

### Phase 1: Data Structures

- [ ] Создать директорию `monsters/`.
- [ ] Создать `_tiers.py` (множители).
- [ ] Создать `_affixes.py` (стихийные модификаторы).
- [ ] Создать `families/orcs.py` (тестовое семейство).
- [ ] Создать `__init__.py` (Реестр с функциями поиска).

### Phase 2: Core Services

- [ ] **`EncounterService`**: Реализовать логику поиска (`find_monster_for_encounter`).
- [ ] **`MonsterFactory`**: Реализовать класс, который:
    -   Принимает `template_id`, `tier`, `affix_id`.
    -   Рассчитывает финальные статы с учетом аффикса и тира.
    -   Вызывает `ModifiersCalculatorService`.
    -   Возвращает `CombatSessionContainerDTO`.

### Phase 3: Battle & Narrative Integration

- [ ] Интеграция `EncounterService` и `MonsterFactory` в боевой движок.
- [ ] Интеграция с LLM для генерации имен и описаний.
- [ ] Наполнение базы (Beasts, Undead, Humans).
