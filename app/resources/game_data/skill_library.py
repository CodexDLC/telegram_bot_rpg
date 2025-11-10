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
        "primary": "strength",
        "secondary": "agility",
        "title_ru": "Ближний бой",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "ranged_combat": {
        "primary": "agility",
        "secondary": "perception",
        "title_ru": "Дальний бой",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "magic_weapons": {
        "primary": "intelligence",
        "secondary": "charisma",
        "title_ru": "Магическое оружие",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },

    # ------------------
    # 🛡 Уровень 1: ЗАЩИТНЫЕ НАВЫКИ
    # ------------------
    "light_armor": {"primary": "endurance", "secondary": "agility", "title_ru": "Легкая броня", "xp_multiplier": 1.0, "prerequisite_skill": None,
                    "prerequisite_title": None},
    "medium_armor": {"primary": "endurance", "secondary": "strength", "title_ru": "Средняя броня", "xp_multiplier": 1.0, "prerequisite_skill": None,
                     "prerequisite_title": None},
    "heavy_armor": {"primary": "strength", "secondary": "endurance", "title_ru": "Тяжелая броня", "xp_multiplier": 1.0, "prerequisite_skill": None,
                    "prerequisite_title": None},
    "shield": {"primary": "strength", "secondary": "agility", "title_ru": "Щит", "xp_multiplier": 1.0, "prerequisite_skill": None,
               "prerequisite_title": None},

    # ------------------
    # 🧠 Уровень 1: ТАКТИЧЕСКИЕ НАВЫКИ
    # ------------------
    "intuition": {"primary": "luck", "secondary": "perception", "title_ru": "Интуиция", "xp_multiplier": 0.8, "prerequisite_skill": None,
                  "prerequisite_title": None},
    "reflexes": {"primary": "agility", "secondary": "perception", "title_ru": "Рефлексы", "xp_multiplier": 0.8, "prerequisite_skill": None,
                 "prerequisite_title": None},
    "fortitude": {"primary": "endurance", "secondary": "strength", "title_ru": "Стойкость", "xp_multiplier": 0.8, "prerequisite_skill": None,
                  "prerequisite_title": None},
    "persistence": {"primary": "strength", "secondary": "endurance", "title_ru": "Настойчивость", "xp_multiplier": 0.8, "prerequisite_skill": None,
                    "prerequisite_title": None},

    # ------------------
    # 🌪️ Уровень 1: ШКОЛЫ МАГИИ Стихий
    # ------------------
    "fire_magic": {"primary": "intelligence", "secondary": "perception", "title_ru": "Магия Огня", "xp_multiplier": 1.2,
                   "prerequisite_skill": None, "prerequisite_title": None},
    "air_magic": {"primary": "intelligence", "secondary": "perception", "title_ru": "Магия Воздуха", "xp_multiplier": 1.2,
                  "prerequisite_skill": None, "prerequisite_title": None},
    "water_magic": {"primary": "intelligence", "secondary": "perception", "title_ru": "Магия Воды", "xp_multiplier": 1.2,
                    "prerequisite_skill": None, "prerequisite_title": None},
    "earth_magic": {"primary": "intelligence", "secondary": "perception", "title_ru": "Магия Земли", "xp_multiplier": 1.2,
                    "prerequisite_skill": None, "prerequisite_title": None},

    # ------------------
    # 🔮 Уровень 1: ШКОЛЫ МАГИИ аспектов
    # ------------------

    "dark_magic": {"primary": "perception", "secondary": "intelligence", "title_ru": "Магия Тьмы", "xp_multiplier": 1.5,
                   "prerequisite_skill": None, "prerequisite_title": None},
    "light_magic": {"primary": "perception", "secondary": "intelligence", "title_ru": "Магия Света", "xp_multiplier": 1.5,
                    "prerequisite_skill": None, "prerequisite_title": None},
    "arcane_magic": {"primary": "perception", "secondary": "intelligence", "title_ru": "Тайная Магия", "xp_multiplier": 1.5,
                     "prerequisite_skill": None, "prerequisite_title": None},
    "nature_magic": {"primary": "charisma", "secondary": "intelligence", "title_ru": "Магия Природы", "xp_multiplier": 1.2, "prerequisite_skill": None,
                "prerequisite_title": None},

    # ------------------
    # 🏗 Уровень 1: БАЗОВЫЕ РЕМЁСЛА (Сбор)
    # ------------------
    "mining": {"primary": "perception", "secondary": "endurance", "title_ru": "Горное дело", "xp_multiplier": 1.0, "prerequisite_skill": None,
               "prerequisite_title": None},
    "herbalism": {"primary": "perception", "secondary": "endurance", "title_ru": "Травничество", "xp_multiplier": 1.0, "prerequisite_skill": None,
                  "prerequisite_title": None},
    "skinning": {"primary": "perception", "secondary": "endurance", "title_ru": "Снятие шкур", "xp_multiplier": 1.0, "prerequisite_skill": None,
                 "prerequisite_title": None},
    "woodcutting": {"primary": "perception", "secondary": "endurance", "title_ru": "Лесорубство", "xp_multiplier": 1.0, "prerequisite_skill": None,
                    "prerequisite_title": None},
    "hunting": {"primary": "perception", "secondary": "endurance", "title_ru": "Охота", "xp_multiplier": 1.0, "prerequisite_skill": None,
                "prerequisite_title": None},
    "archaeology": {"primary": "perception", "secondary": "endurance", "title_ru": "Археология", "xp_multiplier": 1.0, "prerequisite_skill": None,
                    "prerequisite_title": None},
    "gathering": {"primary": "perception", "secondary": "endurance", "title_ru": "Сбор", "xp_multiplier": 1.0, "prerequisite_skill": None,
                  "prerequisite_title": None},

    # ------------------
    # ⚒️ Уровень 1: БАЗОВЫЕ РЕМЁСЛА (Производство)
    # ------------------
    "alchemy": {"primary": "intelligence", "secondary": "agility", "title_ru": "Алхимия", "xp_multiplier": 1.5, "prerequisite_skill": None,
                "prerequisite_title": None},
    "science": {"primary": "intelligence", "secondary": "perception", "title_ru": "Наука", "xp_multiplier": 1.5, "prerequisite_skill": None,
                "prerequisite_title": None},
    "weapon_craft": {"primary": "intelligence", "secondary": "agility", "title_ru": "Оружейное дело", "xp_multiplier": 2.0,
                     "prerequisite_skill": None, "prerequisite_title": None},
    "armor_craft": {"primary": "intelligence", "secondary": "agility", "title_ru": "Бронное дело", "xp_multiplier": 2.0, "prerequisite_skill": None,
                    "prerequisite_title": None},
    "jewelry_craft": {"primary": "intelligence", "secondary": "agility", "title_ru": "Ювелирное дело", "xp_multiplier": 2.0,
                      "prerequisite_skill": None, "prerequisite_title": None},
    "artifact_craft": {"primary": "intelligence", "secondary": "agility", "title_ru": "Создание артефактов", "xp_multiplier": 2.5,
                       "prerequisite_skill": None, "prerequisite_title": None},

    # ------------------
    # 🤝 Уровень 1: БАЗОВЫЕ ТОРГОВЫЕ
    # ------------------
    "accounting": {"primary": "luck", "secondary": "charisma", "title_ru": "Бухгалтерия", "xp_multiplier": 1.0, "prerequisite_skill": None,
                   "prerequisite_title": None},
    "brokerage": {"primary": "luck", "secondary": "charisma", "title_ru": "Посредничество", "xp_multiplier": 1.0, "prerequisite_skill": None,
                  "prerequisite_title": None},
    "contracts": {"primary": "luck", "secondary": "charisma", "title_ru": "Договоры", "xp_multiplier": 1.0, "prerequisite_skill": None,
                  "prerequisite_title": None},
    "trade_relations": {"primary": "luck", "secondary": "charisma", "title_ru": "Торговые связи", "xp_multiplier": 1.0, "prerequisite_skill": None,
                        "prerequisite_title": None},

    # 👥 Уровень 1: БАЗОВЫЕ СОЦИАЛЬНЫЕ

    "leadership": {"primary": "charisma", "secondary": "luck", "title_ru": "Лидерство", "xp_multiplier": 1.0, "prerequisite_skill": None,
                   "prerequisite_title": None},
    "organization": {"primary": "luck", "secondary": "charisma", "title_ru": "Организация", "xp_multiplier": 1.0, "prerequisite_skill": None,
                     "prerequisite_title": None},
    "team_spirit": {"primary": "charisma", "secondary": "luck", "title_ru": "Командный дух", "xp_multiplier": 1.0, "prerequisite_skill": None,
                    "prerequisite_title": None},
    "egoism": {"primary": "luck", "secondary": "charisma", "title_ru": "Эгоизм", "xp_multiplier": 1.0, "prerequisite_skill": None,
               "prerequisite_title": None},

    # ------------------
    # 🚀 Уровень 2: ПРОДВИНУТЫЕ (ADVANCED) НАВЫКИ
    # ------------------
    "advanced_melee_combat": {
        "primary": "strength",
        "secondary": "agility",
        "title_ru": "Продвинутый ближний бой",
        "xp_multiplier": 5.0,  # x5 сложность
        "prerequisite_skill": "melee_combat",
        "prerequisite_title": "⚜️ Грандмастер"
    },
    "advanced_ranged_combat": {
        "primary": "agility",
        "secondary": "perception",
        "title_ru": "Продвинутый дальний бой",
        "xp_multiplier": 5.0,
        "prerequisite_skill": "ranged_combat",
        "prerequisite_title": "⚜️ Грандмастер"
    },
    "advanced_magic_weapons": {
        "primary": "intelligence",
        "secondary": "charisma",
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