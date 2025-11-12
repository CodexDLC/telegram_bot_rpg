# app/resources/game_data/skill_library.py
import logging

log = logging.getLogger(__name__)

# -----------------
# 1. ОБЩАЯ ПЕРЕМЕННАЯ
# -----------------
BASE_MAX_XP = 1_000_000

# -----------------
# 2. РЕЦЕПТЫ S.P.E.C.I.A.L., МУЛЬТИПЛЕЕРЫ И ТРЕБОВАНИЯ
# ВАЖНО: Добавлено поле "title_ru" для UI
# -----------------
SKILL_RECIPES = {

    # ------------------
    # 🗡 Уровень 1: БОЕВЫЕ НАВЫКИ
    # ------------------
    "melee_combat": {
        "stat_weights": {"strength": 2.0, "agility": 1.0},
        "title_ru": "Ближний бой",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "ranged_combat": {
        "stat_weights": {"agility": 2.0, "perception": 1.0},
        "title_ru": "Дальний бой",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "magic_weapons": {
        "stat_weights": {"intelligence": 2.0, "charisma": 1.0},
        "title_ru": "Магическое оружие",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },

    # ------------------
    # 🛡 Уровень 1: ЗАЩИТНЫЕ НАВЫКИ
    # ------------------
    "light_armor": {
        "stat_weights": {"endurance": 2.0, "agility": 1.0},
        "title_ru": "Легкая броня",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "medium_armor": {
        "stat_weights": {"endurance": 2.0, "strength": 1.0},
        "title_ru": "Средняя броня",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "heavy_armor": {
        "stat_weights": {"strength": 2.0, "endurance": 1.0},
        "title_ru": "Тяжелая броня",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "shield": {
        "stat_weights": {"strength": 2.0, "agility": 1.0},
        "title_ru": "Щит",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },

    # ------------------
    # 🧠 Уровень 1: ТАКТИЧЕСКИЕ НАВЫКИ
    # ------------------
    "intuition": {
        "stat_weights": {"agility": 2.0, "wisdom": 1.0},
        "title_ru": "Интуиция",
        "xp_multiplier": 0.8,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "reflexes": {
        "stat_weights": {"wisdom": 2.0, "agility": 1.0},
        "title_ru": "Рефлексы",
        "xp_multiplier": 0.8,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "fortitude": {
        "stat_weights": {"endurance": 2.0, "men": 1.0},
        "title_ru": "Стойкость",
        "xp_multiplier": 0.8,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "persistence": {
        "stat_weights": {"strength": 2.0, "intelligence": 1.0},
        "title_ru": "Настойчивость",
        "xp_multiplier": 0.8,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },

    # ------------------
    # 🌪️ Уровень 1: ШКОЛЫ МАГИИ Стихий
    # ------------------
    "fire_magic": {
        "stat_weights": {"intelligence": 2.0, "wisdom": 1.0},
        "title_ru": "Магия Огня",
        "xp_multiplier": 1.2,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "air_magic": {
        "stat_weights": {"intelligence": 2.0, "wisdom": 1.0},
        "title_ru": "Магия Воздуха",
        "xp_multiplier": 1.2,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "water_magic": {
        "stat_weights": {"intelligence": 2.0, "wisdom": 1.0},
        "title_ru": "Магия Воды",
        "xp_multiplier": 1.2,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "earth_magic": {
        "stat_weights": {"intelligence": 2.0, "wisdom": 1.0},
        "title_ru": "Магия Земли",
        "xp_multiplier": 1.2,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },

    # ------------------
    # 🔮 Уровень 1: ШКОЛЫ МАГИИ аспектов
    # ------------------
    "dark_magic": {
        "stat_weights": {"perception": 2.0, "intelligence": 1.0},
        "title_ru": "Магия Тьмы",
        "xp_multiplier": 1.5,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "light_magic": {
        "stat_weights": {"perception": 2.0, "intelligence": 1.0},
        "title_ru": "Магия Света",
        "xp_multiplier": 1.5,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "arcane_magic": {
        "stat_weights": {"perception": 2.0, "intelligence": 1.0},
        "title_ru": "Тайная Магия",
        "xp_multiplier": 1.5,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "nature_magic": {
        "stat_weights": {"charisma": 2.0, "intelligence": 1.0},
        "title_ru": "Магия Природы",
        "xp_multiplier": 1.2,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },

    # ------------------
    # 🏗 Уровень 1: БАЗОВЫЕ РЕМЁСЛА (Сбор)
    # ------------------
    "mining": {
        "stat_weights": {"perception": 2.0, "endurance": 1.0},
        "title_ru": "Горное дело",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "herbalism": {
        "stat_weights": {"perception": 2.0, "endurance": 1.0},
        "title_ru": "Травничество",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "skinning": {
        "stat_weights": {"perception": 2.0, "endurance": 1.0},
        "title_ru": "Снятие шкур",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "woodcutting": {
        "stat_weights": {"perception": 2.0, "endurance": 1.0},
        "title_ru": "Лесорубство",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "hunting": {
        "stat_weights": {"perception": 2.0, "endurance": 1.0},
        "title_ru": "Охота",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "archaeology": {
        "stat_weights": {"perception": 2.0, "endurance": 1.0},
        "title_ru": "Археология",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "gathering": {
        "stat_weights": {"perception": 2.0, "endurance": 1.0},
        "title_ru": "Сбор",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },

    # ------------------
    # ⚒️ Уровень 1: БАЗОВЫЕ РЕМЁСЛА (Производство)
    # ------------------
    "alchemy": {
        "stat_weights": {"intelligence": 2.0, "agility": 1.0},
        "title_ru": "Алхимия",
        "xp_multiplier": 1.5,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "science": {
        "stat_weights": {"intelligence": 2.0, "perception": 1.0},
        "title_ru": "Наука",
        "xp_multiplier": 1.5,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "weapon_craft": {
        "stat_weights": {"intelligence": 2.0, "agility": 1.0},
        "title_ru": "Оружейное дело",
        "xp_multiplier": 2.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "armor_craft": {
        "stat_weights": {"intelligence": 2.0, "agility": 1.0},
        "title_ru": "Бронное дело",
        "xp_multiplier": 2.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "jewelry_craft": {
        "stat_weights": {"intelligence": 2.0, "agility": 1.0},
        "title_ru": "Ювелирное дело",
        "xp_multiplier": 2.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "artifact_craft": {
        "stat_weights": {"intelligence": 2.0, "agility": 1.0},
        "title_ru": "Создание артефактов",
        "xp_multiplier": 2.5,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },

    # ------------------
    # 🤝 Уровень 1: БАЗОВЫЕ ТОРГОВЫЕ
    # ------------------
    "accounting": {
        "stat_weights": {"luck": 2.0, "charisma": 1.0},
        "title_ru": "Бухгалтерия",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "brokerage": {
        "stat_weights": {"luck": 2.0, "charisma": 1.0},
        "title_ru": "Посредничество",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "contracts": {
        "stat_weights": {"luck": 2.0, "charisma": 1.0},
        "title_ru": "Договоры",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "trade_relations": {
        "stat_weights": {"luck": 2.0, "charisma": 1.0},
        "title_ru": "Торговые связи",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },

    # ------------------
    # 👥 Уровень 1: БАЗОВЫЕ СОЦИАЛЬНЫЕ
    # ------------------
    "leadership": {
        "stat_weights": {"charisma": 2.0, "luck": 1.0},
        "title_ru": "Лидерство",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "organization": {
        "stat_weights": {"luck": 2.0, "charisma": 1.0},
        "title_ru": "Организация",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "team_spirit": {
        "stat_weights": {"charisma": 2.0, "luck": 1.0},
        "title_ru": "Командный дух",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "egoism": {
        "stat_weights": {"luck": 2.0, "charisma": 1.0},
        "title_ru": "Эгоизм",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },

    # ------------------
    # 🚀 Уровень 2: ПРОДВИНУТЫЕ (ADVANCED) НАВЫКИ
    # ------------------
    "advanced_melee_combat": {
        "stat_weights": {"strength": 2.0, "agility": 1.0},
        "title_ru": "Продвинутый ближний бой",
        "xp_multiplier": 5.0,
        "prerequisite_skill": "melee_combat",
        "prerequisite_title": "⚜️ Грандмастер"
    },
    "advanced_ranged_combat": {
        "stat_weights": {"agility": 2.0, "perception": 1.0},
        "title_ru": "Продвинутый дальний бой",
        "xp_multiplier": 5.0,
        "prerequisite_skill": "ranged_combat",
        "prerequisite_title": "⚜️ Грандмастер"
    },
    "advanced_magic_weapons": {
        "stat_weights": {"intelligence": 2.0, "charisma": 1.0},
        "title_ru": "Продвинутое маг. оружие",
        "xp_multiplier": 5.0,
        "prerequisite_skill": "magic_weapons",
        "prerequisite_title": "⚜️ Грандмастер"
    }
}



# 4. ЛОГИКА ПРОГРЕССИИ (Не меняется)
TITLE_THRESHOLDS_PERCENT = {
   100: "🔱 Абсолют",
    75: "⚜️ Гранд-мастер",
    45: "⭐ Мастер",
    25: "🏆 Адепт",
    10: "📗 Продвинутый",
     0: "🌱 Новичок"
}

# 5. КАРТА ГРУПП НАВЫКОВ ДЛЯ UI-МЕНЮ
# (Используется для построения многоуровневых клавиатур в UI Service)
SKILL_UI_GROUPS_MAP = {
    "combat_base": {
        "title_ru": "🗡️ Боевые навыки",
        "skills": {
            "melee_combat": "Ближний бой",
            "ranged_combat": "Дальний бой",
            "magic_weapons": "Магическое оружие",
            "advanced_melee_combat": "Продвинутый ближний бой",
            "advanced_ranged_combat": "Продвинутый дальний бой",
            "advanced_magic_weapons": "Продвинутое маг. оружие",
        }
    },
    "defense_base": {
        "title_ru": "🛡️ Защитные навыки",
        "skills": {
            "light_armor": "Легкая броня",
            "medium_armor": "Средняя броня",
            "heavy_armor": "Тяжелая броня",
            "shield": "Щит",
        }
    },
    "tactical_base": {
        "title_ru": "🧠 Тактические навыки",
        "skills": {
            "intuition": "Интуиция",
            "reflexes": "Рефлексы",
            "fortitude": "Стойкость",
            "persistence": "Настойчивость",
        }
    },
    "magic_elemental": {
        "title_ru": "🌪️ Магия Стихий",
        "skills": {
            "fire_magic": "Магия Огня",
            "air_magic": "Магия Воздуха",
            "water_magic": "Магия Воды",
            "earth_magic": "Магия Земли",
        }
    },
    "magic_aspect": {
        "title_ru": "🔮 Магия Аспектов",
        "skills": {
            "dark_magic": "Магия Тьмы",
            "light_magic": "Магия Света",
            "arcane_magic": "Тайная Магия",
            "nature_magic": "Магия Природы",
        }
    },
    "gathering": {
        "title_ru": "🏗️ Сбор / Ресурсы",
        "skills": {
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
        "title_ru": "⚒️ Производство",
        "skills": {
            "alchemy": "Алхимия",
            "science": "Наука",
            "weapon_craft": "Оружейное дело",
            "armor_craft": "Бронное дело",
            "jewelry_craft": "Ювелирное дело",
            "artifact_craft": "Создание артефактов",
        }
    },
    "trade": {
        "title_ru": "🤝 Торговые",
        "skills": {
            "accounting": "Бухгалтерия",
            "brokerage": "Посредничество",
            "contracts": "Договоры",
            "trade_relations": "Торговые связи",
        }
    },
    "social": {
        "title_ru": "👥 Социальные",
        "skills": {
            "leadership": "Лидерство",
            "organization": "Организация",
            "team_spirit": "Командный дух",
            "egoism": "Эгоизм",
        }
    },
}