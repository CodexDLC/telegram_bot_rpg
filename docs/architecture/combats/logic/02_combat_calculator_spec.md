# Combat Calculator Responsibility (RBC v3.1)

**File:** `apps/game_core/modules/combat/core/combat_calculator.py`
**Type:** Stateless Static Service (Pure Math Engine).

## 1. Философия: Чистая Математика
Калькулятор ничего не знает о "Мечах", "Магии" или "Классах".
Он оперирует только **Числами** и **Флагами** из Контекста.

Паттерн любой функции расчета:
1.  **Check Flag:** Можно ли вообще это делать? (`if not check_evasion: return`)
2.  **Get Base:** Взять базовое значение из статов.
3.  **Apply Modifiers:** Применить множители из контекста (триггеры, баффы).
4.  **Apply Cap:** Обрезать по лимиту.
5.  **Roll:** Бросить кубик.

---

## 2. Архитектура Multi-Source (HitSource)
Вместо того чтобы считать "Один Удар", калькулятор обрабатывает список **Источников Удара** (`HitSource`).

### Зачем это нужно?
*   **Dual Wield:** Атака правой рукой + Атака левой рукой (2 источника).
*   **Double Strike:** Абилка бьет дважды одним оружием (2 одинаковых источника).
*   **Flurry:** Серия из 5 слабых ударов (5 источников).

### Структура HitSource
Каждый источник содержит свои уникальные параметры для расчета:
```python
class HitSourceDTO:
    accuracy: float      # Точность именно этой руки/удара
    crit_chance: float   # Шанс крита именно этой руки
    damage_min: float
    damage_max: float
    armor_pen: float     # Пробитие именно этого удара
    tags: List[str]      # ["main_hand"] или ["off_hand"]
```

### Логика Обработки
Калькулятор проходит по списку `sources` и для каждого выполняет полный цикл проверок (Accuracy -> Damage).
Результаты агрегируются в один `InteractionResult`.

---

## 3. Пример Реализации (Evasion)

```python
def check_evasion(self, context: PipelineContextDTO, source: HitSourceDTO) -> bool:
    # 1. Flag Check (Рубильник)
    if not context.stages.get("check_evasion", True):
        return False # Уворот запрещен

    # 2. Base Value (Защитник)
    evasion_chance = context.defender_stats.evasion

    # 3. Modifiers (Мутация формулы)
    if "evasion_mult" in context.modifiers:
        evasion_chance *= context.modifiers["evasion_mult"]

    # 4. Cap (Лимит)
    cap = context.caps.get("evasion_cap", 0.75)
    evasion_chance = min(evasion_chance, cap)

    # 5. Final Roll (Accuracy берется из SOURCE)
    hit_chance = source.accuracy * (1.0 - evasion_chance)
    return random.random() > hit_chance
```

---

## 4. Обязанности (What it DOES)

### А. Интерпретация Флагов
*   `force_miss` -> Вернуть 0 урона.
*   `force_hit` -> Пропустить проверку точности.
*   `ignore_block` -> Считать, что `block_zones` пустой.

### Б. Расчет Контакта (Resolution)
*   **Accuracy Check:** HitRate vs Evasion.
*   **Zone Check:** Пересечение зон атаки и блока.

### В. Математика Урона
1.  **Base Roll:** Random(Min, Max).
2.  **Multipliers:** `* SkillPower * CritMod`.
3.  **Mitigation:** `(Damage * (1 - Resist)) - FlatArmor`.

---

## 5. Запреты (What it DOES NOT)
*   ❌ **НЕ меняет State:** Никаких `hp -= damage`.
*   ❌ **НЕ лезет в Базу:** Работает только с DTO.
*   ❌ **НЕ знает про Игровые Сущности:** Никаких `if weapon.type == 'sword'`. Только `if context.flags['is_sword_style']`.
