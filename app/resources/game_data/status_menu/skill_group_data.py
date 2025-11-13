# app/resources/game_data/status_menu/skill_group_data.py
import logging
from typing import Dict, Any

# 1. Импортируем "Мастер-список" вкладок из "Био"
# (Предполагается, что bio_group_data.py находится в этой же папке)
from .bio_group_data import TABS_NAV_DATA

log = logging.getLogger(__name__)

# ==========================================================================
# ИЕРАРХИЯ ДАННЫХ ДЛЯ ВКЛАДКИ "НАВЫКИ" (SKILLS)
# ==========================================================================
# Этот словарь будет парсить SkillService.
# Он построен на основе SKILL_UI_GROUPS_MAP из skill_library.py
# ==========================================================================
SKILL_HIERARCHY: Dict[str, Any] = {

    # === LEVEL 0 (Вкладка) ===
    # Ключ 'skills' (из TABS_NAV_DATA)
    "skills": {
        "title": "📚 Навыки",
        "description": (
            "Здесь собраны все твои разблокированные навыки. "
            "Выбери группу для просмотра."
        ),
        # "items" - это то, что станет кнопками Level 1
        "items": {
            "combat_base": "🗡️ Боевые навыки",
            "defense_base": "🛡️ Защитные навыки",
            "tactical_base": "🧠 Тактические навыки",
            "magic_elemental": "🌪️ Магия Стихий",
            "magic_aspect": "🔮 Магия Аспектов",
            "gathering": "🏗️ Сбор / Ресурсы",
            "production": "⚒️ Производство",
            "trade": "🤝 Торговые",
            "social": "👥 Социальные",
        }
    },

    # === LEVEL 1 (Группы) ===
    # Ключи 'combat_base', 'defense_base' и т.д. (из "items" выше)

    "combat_base": {
        "title": "🗡️ Боевые навыки",
        "description": "Группа навыков, отвечающих за ведение боя.",
        "empty_description": "У тебя пока нет разблокированных боевых навыков.",
        "data_source": "character_progress_skill",
        "items": {
            "melee_combat": "Ближний бой",
            "ranged_combat": "Дальний бой",
            "magic_weapons": "Магическое оружие",
            "advanced_melee_combat": "Продвинутый ближний бой",
            "advanced_ranged_combat": "Продвинутый дальний бой",
            "advanced_magic_weapons": "Продвинутое маг. оружие",
        }
    },

    "defense_base": {
        "title": "🛡️ Защитные навыки",
        "description": "Группа навыков, отвечающих за твою выживаемость.",
        "empty_description": "У тебя пока нет разблокированных защитных навыков.",
        "data_source": "character_progress_skill",
        "items": {
            "light_armor": "Легкая броня",
            "medium_armor": "Средняя броня",
            "heavy_armor": "Тяжелая броня",
            "shield": "Щит",
        }
    },

    "tactical_base": {
        "title": "🧠 Тактические навыки",
        "description": "Группа навыков, отвечающих за тактическое преимущество.",
        "empty_description": "У тебя пока нет разблокированных тактических навыков.",
        "data_source": "character_progress_skill",
        "items": {
            "intuition": "Интуиция",
            "reflexes": "Рефлексы",
            "fortitude": "Стойкость",
            "persistence": "Настойчивость",
        }
    },

    "magic_elemental": {
        "title": "🌪️ Магия Стихий",
        "description": "Группа навыков, отвечающих за магию стихий.",
        "empty_description": "У тебя пока нет разблокированных навыков магии стихий.",
        "data_source": "character_progress_skill",
        "items": {
            "fire_magic": "Магия Огня",
            "air_magic": "Магия Воздуха",
            "water_magic": "Магия Воды",
            "earth_magic": "Магия Земли",
        }
    },

    "magic_aspect": {
        "title": "🔮 Магия Аспектов",
        "description": "Группа навыков, отвечающих за магию аспектов.",
        "empty_description": "У тебя пока нет разблокированных навыков магии аспектов.",
        "data_source": "character_progress_skill",
        "items": {
            "dark_magic": "Магия Тьмы",
            "light_magic": "Магия Света",
            "arcane_magic": "Тайная Магия",
            "nature_magic": "Магия Природы",
        }
    },

    "gathering": {
        "title": "🏗️ Сбор / Ресурсы",
        "description": "Группа навыков, отвечающих за сбор ресурсов.",
        "empty_description": "У тебя пока нет разблокированных навыков сбора.",
        "data_source": "character_progress_skill",
        "items": {
            "mining": "Горное дело",
            "herbalism": "Травничество",
            "skinning": "Снятие шкур",
            "woodcutting": "Лесорубство",
            "hunting": "Охота",
            "archaeology": "Археология",
            "gathering": "Сбор",
        }
    },

    "production": {
        "title": "⚒️ Производство",
        "description": "Группа навыков, отвечающих за создание предметов.",
        "empty_description": "У тебя пока нет разблокированных производственных навыков.",
        "data_source": "character_progress_skill",
        "items": {
            "alchemy": "Алхимия",
            "science": "Наука",
            "weapon_craft": "Оружейное дело",
            "armor_craft": "Бронное дело",
            "jewelry_craft": "Ювелирное дело",
            "artifact_craft": "Создание артефактов",
        }
    },

    "trade": {
        "title": "🤝 Торговые",
        "description": "Группа навыков, отвечающих за торговлю.",
        "empty_description": "У тебя пока нет разблокированных торговых навыков.",
        "data_source": "character_progress_skill",
        "items": {
            "accounting": "Бухгалтерия",
            "brokerage": "Посредничество",
            "contracts": "Договоры",
            "trade_relations": "Торговые связи",
        }
    },

    "social": {
        "title": "👥 Социальные",
        "description": "Группа навыков, отвечающих за социальное взаимодействие.",
        "empty_description": "У тебя пока нет разблокированных социальных навыков.",
        "data_source": "character_progress_skill",
        "items": {
            "leadership": "Лидерство",
            "organization": "Организация",
            "team_spirit": "Командный дух",
            "egoism": "Эгоизм",
        }
    },


    # === LEVEL 2 (Детали) ===
    # Ключи 'melee_combat', 'light_armor' и т.д.
    # (Описание для *каждого* навыка)

    # --- Combat ---
    "melee_combat": {
        "title": "Ближний бой",
        "description": (
            "<b>Ближний бой (Melee Combat)</b>\n"
            "Навык определяет мастерство владения оружием ближнего боя.\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "ranged_combat": {
        "title": "Дальний бой",
        "description": (
            "<b>Дальний бой (Ranged Combat)</b>\n"
            "Навык определяет мастерство владения оружием дальнего боя.\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "magic_weapons": {
        "title": "Магическое оружие",
        "description": (
            "<b>Магическое оружие (Magic Weapons)</b>\n"
            "Навык определяет мастерство владения магическим оружием.\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "advanced_melee_combat": {
        "title": "Продвинутый ближний бой",
        "description": (
            "<b>Продвинутый ближний бой (Advanced Melee Combat)</b>\n"
            "Продвинутый навык владения оружием ближнего боя.\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "advanced_ranged_combat": {
        "title": "Продвинутый дальний бой",
        "description": (
            "<b>Продвинутый дальний бой (Advanced Ranged Combat)</b>\n"
            "Продвинутый навык владения оружием дальнего боя.\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "advanced_magic_weapons": {
        "title": "Продвинутое маг. оружие",
        "description": (
            "<b>Продвинутое маг. оружие (Advanced Magic Weapons)</b>\n"
            "Продвинутый навык владения магическим оружием.\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },

    # --- Defense ---
    "light_armor": {
        "title": "Легкая броня",
        "description": (
            "<b>Легкая броня (Light Armor)</b>\n"
            "Навык определяет эффективность ношения легкой брони.\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "medium_armor": {
        "title": "Средняя броня",
        "description": (
            "<b>Средняя броня (Medium Armor)</b>\n"
            "Навык определяет эффективность ношения средней брони.\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "heavy_armor": {
        "title": "Тяжелая броня",
        "description": (
            "<b>Тяжелая броня (Heavy Armor)</b>\n"
            "Навык определяет эффективность ношения тяжелой брони.\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "shield": {
        "title": "Щит",
        "description": (
            "<b>Щит (Shield)</b>\n"
            "Навык определяет эффективность использования щита.\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },

    # --- Tactical ---
    "intuition": {
        "title": "Интуиция",
        "description": (
            "<b>Интуиция (Intuition)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "reflexes": {
        "title": "Рефлексы",
        "description": (
            "<b>Рефлексы (Reflexes)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "fortitude": {
        "title": "Стойкость",
        "description": (
            "<b>Стойкость (Fortitude)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "persistence": {
        "title": "Настойчивость",
        "description": (
            "<b>Настойчивость (Persistence)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },

    # --- Magic Elemental ---
    "fire_magic": {
        "title": "Магия Огня",
        "description": (
            "<b>Магия Огня (Fire Magic)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "air_magic": {
        "title": "Магия Воздуха",
        "description": (
            "<b>Магия Воздуха (Air Magic)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "water_magic": {
        "title": "Магия Воды",
        "description": (
            "<b>Магия Воды (Water Magic)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "earth_magic": {
        "title": "Магия Земли",
        "description": (
            "<b>Магия Земли (Earth Magic)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },

    # --- Magic Aspect ---
    "dark_magic": {
        "title": "Магия Тьмы",
        "description": (
            "<b>Магия Тьмы (Dark Magic)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "light_magic": {
        "title": "Магия Света",
        "description": (
            "<b>Магия Света (Light Magic)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "arcane_magic": {
        "title": "Тайная Магия",
        "description": (
            "<b>Тайная Магия (Arcane Magic)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "nature_magic": {
        "title": "Магия Природы",
        "description": (
            "<b>Магия Природы (Nature Magic)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },

    # --- Gathering ---
    "mining": {
        "title": "Горное дело",
        "description": (
            "<b>Горное дело (Mining)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "herbalism": {
        "title": "Травничество",
        "description": (
            "<b>Травничество (Herbalism)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "skinning": {
        "title": "Снятие шкур",
        "description": (
            "<b>Снятие шкур (Skinning)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "woodcutting": {
        "title": "Лесорубство",
        "description": (
            "<b>Лесорубство (Woodcutting)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "hunting": {
        "title": "Охота",
        "description": (
            "<b>Охота (Hunting)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "archaeology": {
        "title": "Археология",
        "description": (
            "<b>Археология (Archaeology)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "gathering": {
        "title": "Сбор",
        "description": (
            "<b>Сбор (Gathering)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },

    # --- Production ---
    "alchemy": {
        "title": "Алхимия",
        "description": (
            "<b>Алхимия (Alchemy)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "science": {
        "title": "Наука",
        "description": (
            "<b>Наука (Science)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "weapon_craft": {
        "title": "Оружейное дело",
        "description": (
            "<b>Оружейное дело (Weapon Craft)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "armor_craft": {
        "title": "Бронное дело",
        "description": (
            "<b>Бронное дело (Armor Craft)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "jewelry_craft": {
        "title": "Ювелирное дело",
        "description": (
            "<b>Ювелирное дело (Jewelry Craft)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "artifact_craft": {
        "title": "Создание артефактов",
        "description": (
            "<b>Создание артефактов (Artifact Craft)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },

    # --- Trade ---
    "accounting": {
        "title": "Бухгалтерия",
        "description": (
            "<b>Бухгалтерия (Accounting)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "brokerage": {
        "title": "Посредничество",
        "description": (
            "<b>Посредничество (Brokerage)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "contracts": {
        "title": "Договоры",
        "description": (
            "<b>Договоры (Contracts)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "trade_relations": {
        "title": "Торговые связи",
        "description": (
            "<b>Торговые связи (Trade Relations)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },

    # --- Social ---
    "leadership": {
        "title": "Лидерство",
        "description": (
            "<b>Лидерство (Leadership)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "organization": {
        "title": "Организация",
        "description": (
            "<b>Организация (Organization)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "team_spirit": {
        "title": "Командный дух",
        "description": (
            "<b>Командный дух (Team Spirit)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
    "egoism": {
        "title": "Эгоизм",
        "description": (
            "<b>Эгоизм (Egoism)</b>\n"
            "(Описание в разработке...)\n\n"
            "<b>Статус:</b> {skill.status}\n"
            "<b>Прогресс:</b> {skill.percentage}%\n"
            "<b>Звание:</b> {skill.title}"
        ),
        "data_source": "character_progress_skill", "items": None
    },
}