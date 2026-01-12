# Skills (Пассивные навыки)

## 📋 Обзор

Этот документ описывает **техническую реализацию** хранения и конфигурации навыков в `Game Data Library`.
Философия и игровая механика навыков описаны в [архитектурной документации](../../skills/README.md).

Здесь мы фокусируемся на том, как навыки представлены в коде (DTO) и как они загружаются.

## ⚙️ Техническая реализация

### Структура DTO

Все навыки описываются единой моделью `SkillDTO`:

```python
from pydantic import BaseModel
from enum import Enum

class SkillCategory(str, Enum):
    COMBAT = "combat"
    NON_COMBAT = "non_combat"

class SkillGroup(str, Enum):
    WEAPON_MASTERY = "weapon_mastery"
    ARMOR = "armor"
    TACTICAL = "tactical"
    COMBAT_SUPPORT = "combat_support"
    GATHERING = "gathering"
    CRAFTING = "crafting"
    TRADE = "trade"
    SOCIAL = "social"
    SURVIVAL = "survival"

class SkillDTO(BaseModel):
    skill_key: str              # Уникальный ключ (например, "skill_swords")
    name_en: str                # Название (EN)
    name_ru: str                # Название (RU)
    
    category: SkillCategory     # Категория (Combat / Non-Combat)
    group: SkillGroup           # Группа (Weapon Mastery, Armor, ...)
    
    # Математика прогрессии (влияет на скорость прокачки)
    stat_weights: dict[str, int] # Веса атрибутов {"strength": 2, "agility": 1}
    rate_mod: float             # Множитель скорости (1.0 = стандарт)
    wall_mod: float             # Множитель сложности капа (1.0 = стандарт)
    
    description: str            # Описание для UI
```

### Пример конфигурации (Swords)

```python
# apps/game_core/resources/game_data/skills/definitions/skills/weapon_mastery.py

swords_config = SkillDTO(
    skill_key="skill_swords",
    name_en="Swordsmanship",
    name_ru="Владение мечами",
    category=SkillCategory.COMBAT,
    group=SkillGroup.WEAPON_MASTERY,
    stat_weights={"strength": 2, "agility": 1, "endurance": 1},
    rate_mod=1.0,
    wall_mod=1.0,
    description="Мастерство владения мечами. Повышает точность и стабилизирует урон."
)
```

## 🔌 Интеграция в боевую систему

Навыки не имеют "эффектов" в привычном понимании (как абилки). Они используются как **коэффициенты** в формулах `CombatResolver`.

### Пример использования в коде

```python
# В CombatResolver (расчет шанса крита)
def calculate_crit_chance(attacker_stats):
    base_crit = attacker_stats.modifiers.crit_chance
    
    # Получаем текущее значение навыка (0.0 - 100.0)
    skill_val = attacker_stats.skills.skill_swords 
    
    # Навык работает как множитель
    skill_multiplier = 1.0 + (skill_val / 100.0) 
    
    final_crit_chance = base_crit * skill_multiplier
    return final_crit_chance
```

## 📦 Registry & Access

Доступ к конфигам осуществляется через фасад модуля `game_data.skills`.

```python
# apps/game_core/resources/game_data/skills/__init__.py

SKILL_REGISTRY: dict[str, SkillDTO] = {
    "skill_swords": swords_config,
    # ... остальные навыки
}

def get_skill_config(skill_key: str) -> SkillDTO | None:
    """Получить конфиг навыка по ключу (O(1))."""
    return SKILL_REGISTRY.get(skill_key)
```

## 🔗 Связанные документы

*   [Архитектура навыков](../../skills/README.md) — Полное описание механик и философии.
*   [Progression Math](../../skills/core_mechanics/progression_math.md) — Формулы прокачки.
