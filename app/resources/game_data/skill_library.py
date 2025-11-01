# app/resources/game_data/skill_library.py
import logging

log = logging.getLogger(__name__)

# -----------------
# 1. ОБЩАЯ ПЕРЕМЕННАЯ
# -----------------
BASE_MAX_XP = 1_000_000

# -----------------
# 2. РЕЦЕПТЫ S.P.E.C.I.A.L., МУЛЬТИПЛЕЕРЫ И ТРЕБОВАНИЯ
# (Твоя полная EVE-модель)
# -----------------
SKILL_RECIPES = {

    # ------------------
    # 🗡 Уровень 1: БАЗОВЫЕ БОЕВЫЕ НАВЫКИ
    # ------------------
    "melee_combat": {
        "primary": "strength",
        "secondary": "agility",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "ranged_combat": {
        "primary": "agility",
        "secondary": "perception",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },
    "magic_weapons": {
        "primary": "intelligence",
        "secondary": "charisma",
        "xp_multiplier": 1.0,
        "prerequisite_skill": None,
        "prerequisite_title": None
    },

    # ------------------
    # 🛡 Уровень 1: БАЗОВЫЕ ЗАЩИТНЫЕ НАВЫКИ
    # ------------------
    "light_armor": {"primary": "endurance", "secondary": "agility", "xp_multiplier": 1.0, "prerequisite_skill": None,
                    "prerequisite_title": None},
    "medium_armor": {"primary": "endurance", "secondary": "strength", "xp_multiplier": 1.0, "prerequisite_skill": None,
                     "prerequisite_title": None},
    "heavy_armor": {"primary": "strength", "secondary": "endurance", "xp_multiplier": 1.0, "prerequisite_skill": None,
                    "prerequisite_title": None},
    "shield": {"primary": "strength", "secondary": "agility", "xp_multiplier": 1.0, "prerequisite_skill": None,
               "prerequisite_title": None},

    # ------------------
    # 🧠 Уровень 1: БАЗОВЫЕ ТАКТИЧЕСКИЕ НАВЫКИ
    # ------------------
    "intuition": {"primary": "luck", "secondary": "perception", "xp_multiplier": 0.8, "prerequisite_skill": None,
                  "prerequisite_title": None},
    "reflexes": {"primary": "agility", "secondary": "perception", "xp_multiplier": 0.8, "prerequisite_skill": None,
                 "prerequisite_title": None},
    "fortitude": {"primary": "endurance", "secondary": "strength", "xp_multiplier": 0.8, "prerequisite_skill": None,
                  "prerequisite_title": None},
    "persistence": {"primary": "strength", "secondary": "endurance", "xp_multiplier": 0.8, "prerequisite_skill": None,
                    "prerequisite_title": None},

    # ------------------
    # 🌪️ Уровень 1: ШКОЛЫ МАГИИ Стихий
    # ------------------
    "fire_magic": {"primary": "intelligence", "secondary": "perception", "xp_multiplier": 1.2,
                   "prerequisite_skill": None, "prerequisite_title": None},
    "air_magic": {"primary": "intelligence", "secondary": "perception", "xp_multiplier": 1.2,
                  "prerequisite_skill": None, "prerequisite_title": None},
    "water_magic": {"primary": "intelligence", "secondary": "perception", "xp_multiplier": 1.2,
                    "prerequisite_skill": None, "prerequisite_title": None},
    "earth_magic": {"primary": "intelligence", "secondary": "perception", "xp_multiplier": 1.2,
                    "prerequisite_skill": None, "prerequisite_title": None},

    # ------------------
    # 🔮 Уровень 1: ШКОЛЫ МАГИИ аспектов
    # ------------------

    "dark_magic": {"primary": "perception", "secondary": "intelligence", "xp_multiplier": 1.5,
                   "prerequisite_skill": None, "prerequisite_title": None},
    "light_magic": {"primary": "perception", "secondary": "intelligence", "xp_multiplier": 1.5,
                    "prerequisite_skill": None, "prerequisite_title": None},
    "arcane_magic": {"primary": "perception", "secondary": "intelligence", "xp_multiplier": 1.5,
                     "prerequisite_skill": None, "prerequisite_title": None},
    "nature_magic": {"primary": "charisma", "secondary": "intelligence", "xp_multiplier": 1.2, "prerequisite_skill": None,
                "prerequisite_title": None},

    # ------------------
    # 🏗 Уровень 1: БАЗОВЫЕ РЕМЁСЛА
    # ------------------
    "mining": {"primary": "perception", "secondary": "endurance", "xp_multiplier": 1.0, "prerequisite_skill": None,
               "prerequisite_title": None},
    "herbalism": {"primary": "perception", "secondary": "endurance", "xp_multiplier": 1.0, "prerequisite_skill": None,
                  "prerequisite_title": None},
    "skinning": {"primary": "perception", "secondary": "endurance", "xp_multiplier": 1.0, "prerequisite_skill": None,
                 "prerequisite_title": None},
    "woodcutting": {"primary": "perception", "secondary": "endurance", "xp_multiplier": 1.0, "prerequisite_skill": None,
                    "prerequisite_title": None},
    "hunting": {"primary": "perception", "secondary": "endurance", "xp_multiplier": 1.0, "prerequisite_skill": None,
                "prerequisite_title": None},
    "archaeology": {"primary": "perception", "secondary": "endurance", "xp_multiplier": 1.0, "prerequisite_skill": None,
                    "prerequisite_title": None},
    "gathering": {"primary": "perception", "secondary": "endurance", "xp_multiplier": 1.0, "prerequisite_skill": None,
                  "prerequisite_title": None},

    # ------------------
    # ⚒️ Уровень 1: БАЗОВЫЕ РЕМЁСЛА (Производство)
    # ------------------
    "alchemy": {"primary": "intelligence", "secondary": "agility", "xp_multiplier": 1.5, "prerequisite_skill": None,
                "prerequisite_title": None},
    "science": {"primary": "intelligence", "secondary": "perception", "xp_multiplier": 1.5, "prerequisite_skill": None,
                "prerequisite_title": None},
    "weapon_craft": {"primary": "intelligence", "secondary": "agility", "xp_multiplier": 2.0,
                     "prerequisite_skill": None, "prerequisite_title": None},
    "armor_craft": {"primary": "intelligence", "secondary": "agility", "xp_multiplier": 2.0, "prerequisite_skill": None,
                    "prerequisite_title": None},
    "jewelry_craft": {"primary": "intelligence", "secondary": "agility", "xp_multiplier": 2.0,
                      "prerequisite_skill": None, "prerequisite_title": None},
    "artifact_craft": {"primary": "intelligence", "secondary": "agility", "xp_multiplier": 2.5,
                       "prerequisite_skill": None, "prerequisite_title": None},

    # ------------------
    # 🤝 Уровень 1: БАЗОВЫЕ ТОРГОВЫЕ
    # ------------------
    "accounting": {"primary": "luck", "secondary": "charisma", "xp_multiplier": 1.0, "prerequisite_skill": None,
                   "prerequisite_title": None},
    "brokerage": {"primary": "luck", "secondary": "charisma", "xp_multiplier": 1.0, "prerequisite_skill": None,
                  "prerequisite_title": None},
    "contracts": {"primary": "luck", "secondary": "charisma", "xp_multiplier": 1.0, "prerequisite_skill": None,
                  "prerequisite_title": None},
    "trade_relations": {"primary": "luck", "secondary": "charisma", "xp_multiplier": 1.0, "prerequisite_skill": None,
                        "prerequisite_title": None},

    # 🤝 Уровень 1: БАЗОВЫЕ СОЦИАЛЬНЫЕ

    "leadership": {"primary": "charisma", "secondary": "luck", "xp_multiplier": 1.0, "prerequisite_skill": None,
                   "prerequisite_title": None},
    "organization": {"primary": "luck", "secondary": "charisma", "xp_multiplier": 1.0, "prerequisite_skill": None,
                     "prerequisite_title": None},
    "team_spirit": {"primary": "charisma", "secondary": "luck", "xp_multiplier": 1.0, "prerequisite_skill": None,
                    "prerequisite_title": None},
    "egoism": {"primary": "luck", "secondary": "charisma", "xp_multiplier": 1.0, "prerequisite_skill": None,
               "prerequisite_title": None},

    # ------------------
    # 🚀 Уровень 2: ПРОДВИНУТЫЕ (ADVANCED) НАВЫКИ
    # ------------------
    "advanced_melee_combat": {
        "primary": "strength",
        "secondary": "agility",
        "xp_multiplier": 5.0,  # x5 сложность
        "prerequisite_skill": "melee_combat",
        "prerequisite_title": "⚜️ Грандмастер"
    },
    "advanced_ranged_combat": {
        "primary": "agility",
        "secondary": "perception",
        "xp_multiplier": 5.0,
        "prerequisite_skill": "ranged_combat",
        "prerequisite_title": "⚜️ Грандмастер"
    },
    "advanced_magic_weapons": {
        "primary": "intelligence",
        "secondary": "charisma",
        "xp_multiplier": 5.0,
        "prerequisite_skill": "magic_weapons",
        "prerequisite_title": "⚜️ Грандмастер"
    }
}

# 3. ГРУППЫ НАВЫКОВ (для авто-прокачки)
SKILL_GROUPS = {
    # 🗡 Авто-охота
    "auto_hunt": [
        "melee_combat", "ranged_combat",
        "advanced_melee_combat", "advanced_ranged_combat",
        "intuition", "reflexes", "fortitude", "persistence",
        "light_armor", "medium_armor", "heavy_armor", "shield",
    ],

    # 🏗 Экспедиции в эпицентры (Добыча)
    "expeditions": [
        "mining", "herbalism", "skinning", "woodcutting",
        "hunting", "archaeology", "gathering",
    ],

    # 🤝 Торговый квартал (Социальные и Торговые)
    "trade_quarter": [
        "accounting", "brokerage", "contracts", "trade_relations",
        "leadership", "organization", "team_spirit", "egoism",
    ],

    # 🏭 Производственный квартал
    "production_quarter": [
        "weapon_craft", "armor_craft", "jewelry_craft", "artifact_craft",
        "alchemy", "science",
    ],

    # 🏫 Академия энергоконструкции (Магия и Поддержка)
    "academy": [
        "magic_weapons", "advanced_magic_weapons",
        "fire_magic", "air_magic", "water_magic", "earth_magic",
        "dark_magic", "light_magic", "arcane_magic",
        "advanced_fire_magic", "advanced_water_magic",  # ...
        "healing",
    ],
}

# 4. ЛОГИКА ПРОГРЕССИИ (Не меняется)
TITLE_THRESHOLDS_PERCENT = {
    90: "⚜️ Грандмастер",
    70: "⭐ Мастер",
    40: "🏆 Адепт",
    10: "📗 Продвинутый",
    0: "🌱 Новичок"
}

