# Game Data Library

Централизованное хранилище всех игровых конфигов (Skills, Abilities, Triggers, Effects).

## Философия

Все игровые данные хранятся как **Python словари** в памяти приложения.

**Принципы:**
1. **Единый паттерн:** Все библиотеки используют одинаковую структуру (Registry + DTO + API)
2. **Быстрый доступ:** O(1) поиск по ключу
3. **Типизация:** Pydantic DTO для валидации
4. **Ленивая загрузка:** Автоинициализация при импорте модуля

## Структура
```
apps/game_core/resources/game_data/
├── __init__.py                         # Public API (get_skill, get_ability, ...)
│
├── skills/                              # ✅ Уже есть
│   ├── __init__.py                      # Registry + API
│   ├── schemas.py                       # DTO: SkillDTO
│   └── definitions/
│       └── skills/
│           ├── weapon_mastery.py
│           ├── armor.py
│           └── ...
│
├── abilities/                           # ❌ Новое (Абилки)
│   ├── __init__.py                      # Registry + API
│   ├── schemas.py                       # DTO: AbilityDTO
│   └── definitions/
│       ├── combat/                      # Боевые
│       │   ├── offensive.py             # Fireball, Lightning
│       │   ├── defensive.py             # Shield, Barrier
│       │   └── control.py               # Stun, Slow
│       └── support/                     # Утилиты
│           ├── buffs.py                 # Rage, Haste
│           ├── heals.py                 # Heal, Regeneration
│           └── debuffs.py               # Poison, Weakness
│
├── triggers/                            # ❌ Новое (Триггеры оружия)
│   ├── __init__.py                      # Registry + API
│   ├── schemas.py                       # DTO: TriggerDTO
│   └── definitions/
│       ├── weapon_triggers.py           # Триггеры по классам оружия
│       └── trigger_rules.py             # TRIGGER_RULES (мутации)
│
├── feints/                              # ❌ Новое (Финты)
│   ├── __init__.py                      # Registry + API
│   ├── schemas.py                       # DTO: FeintDTO
│   └── definitions/
│       ├── swords.py                    # Финты мечей
│       ├── macing.py                    # Финты молотов
│       ├── archery.py                   # Финты луков
│       └── unarmed.py                   # Финты безоружного
│
├── effects/                             # ❌ Новое (Эффекты: DoT, Buff, Control)
│   ├── __init__.py                      # Registry + API
│   ├── schemas.py                       # DTO: EffectDTO
│   └── definitions/
│       ├── dots.py                      # Bleed, Poison, Burn
│       ├── buffs.py                     # Rage, Shield
│       ├── debuffs.py                   # Weakness, Slow
│       └── control.py                   # Stun, Sleep, Root
│
└── shared/                              # Общие утилиты
    ├── flag_configs.py                  # FlagConfig (TypedDict)
    └── validation.py                    # Валидаторы
```

## Паттерн использования
```python
# Импорт
from apps.game_core.resources.game_data.skills import get_skill_config
from apps.game_core.resources.game_data.abilities import get_ability_config

# Использование
skill = get_skill_config("skill_swords")
ability = get_ability_config("fireball")
```

## Компоненты

- **[Skills](./skills.md)** — Пассивные навыки
- **[Abilities](./abilities.md)** — Активные способности
- **[Triggers](./triggers.md)** — Триггеры оружия
- **[Feints](./feints.md)** — Специальные приемы
- **[Effects](./effects.md)** — Статусные эффекты
