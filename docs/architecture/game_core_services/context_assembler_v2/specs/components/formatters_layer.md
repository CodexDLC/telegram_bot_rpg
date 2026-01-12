# Formatters Layer (Logic Helpers)

## Назначение
Этот слой описывает **логику трансформации данных**, которая используется внутри `TempContext` DTO (в методах `@computed_field`).
В текущей реализации (v2.0) это не отдельные классы, а набор вспомогательных функций (helpers) или приватных методов внутри DTO.

## Основные задачи

### 1. Skills Formatting
**Цель:** Преобразование списка `SkillProgressDTO` в структуру для `math_model`.
**Логика:**
*   Вход: `list[SkillProgressDTO]`
*   Действие:
    *   Фильтрация (только `is_unlocked=True`?).
    *   Маппинг: `skill.skill_key` -> `value` (total_xp).
*   Выход: `dict[str, float]` (например, `{"skill_swords": 0.55}`).

### 2. Stats Calculation
**Цель:** Расчет итоговых атрибутов и модификаторов от экипировки.
**Логика:**
*   Вход: `CharacterAttributesReadDTO`, `list[InventoryItemDTO]` (equipped).
*   Действие:
    *   Суммирование базовых статов.
    *   Извлечение бонусов из предметов (`implicit_bonuses`, `explicit_bonuses`).
    *   Форматирование значений (строки для simpleeval).
*   Выход: Структура `v:raw` (`attributes`, `modifiers`).

### 3. Inventory Grouping
**Цель:** Группировка предметов для UI.
**Логика:**
*   Вход: `list[InventoryItemDTO]`.
*   Действие:
    *   Группировка по слотам (`equipped_slot`).
    *   Группировка по типам (`item_type`).
*   Выход: Словари для `InventoryTempContext`.

## Будущее развитие
Если логика форматирования станет слишком сложной для DTO, она будет вынесена в отдельные классы-форматтеры (`SkillsFormatter`, `StatsFormatter`), которые будут вызываться из DTO.
