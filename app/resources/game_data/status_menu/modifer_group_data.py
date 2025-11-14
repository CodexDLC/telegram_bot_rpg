# app/resources/game_data/status_menu/modifier_group_data.py
import logging
from typing import Dict, Any

# 1. Импортируем "Мастер-список" вкладок из "Био"
# (Предполагается, что bio_group_data.py находится в этой же папке)
from .bio_group_data import TABS_NAV_DATA

log = logging.getLogger(__name__)

# ==========================================================================
# ИЕРАРХИЯ ДАННЫХ ДЛЯ ВКЛАДКИ "МОДИФИКАТОРЫ" (STATS)
# ==========================================================================
# Этот словарь будет парсить StatsService
# Он построен на основе MODIFIER_UI_GROUPS_MAP из modifer_library.py
# ==========================================================================
MODIFIER_HIERARCHY: Dict[str, Any] = {

    # === LEVEL 0 (Вкладка) ===
    # Ключ 'stats' (из TABS_NAV_DATA)
    "stats": {
        "title": "❤️ Модификаторы",
        "description": (
            "Здесь собраны твои базовые характеристики (Lvl 1) и все "
            "производные модификаторы (Lvl 2), которые влияют на бой и мир."
        ),
        # "items" - это то, что станет кнопками Level 1
        "items": {
            "base_stats": "❤️ Базовые Характеристики (Lvl 1)",
            "resources": "🩸 Ресурсы (Lvl 2)",
            "physical_offense": "⚔️ Физическая Атака (Lvl 2)",
            "magical_offense": "🔮 Магическая Атака (Lvl 2)",
            "defense": "🛡️ Защита (Lvl 2)",
            "general_combat": "✨ Общие Боевые (Lvl 2)",
            "utility": "💰 Экономика и Ремесло (Lvl 2)",
        }
    },

    # === LEVEL 1 (Группы) ===
    # Ключи 'base_stats', 'resources' и т.д. (из "items" выше)

    "base_stats": {
        "title": "❤️ Базовые Характеристики (Lvl 1)",
        "description": "Твои 9 основных характеристик. Они являются 'Lvl 1' и определяют все остальные параметры.",
          # Подсказка сервису, какой DTO парсить
        "items": {
            "strength": "Сила",
            "agility": "Ловкость",
            "endurance": "Выносливость",
            "intelligence": "Интеллект",
            "wisdom": "Мудрость",
            "men": "Дух",
            "perception": "Восприятие",
            "charisma": "Харизма",
            "luck": "Удача",
        }
    },

    "resources": {
        "title": "🩸 Ресурсы (Lvl 2)",
        "description": "Модификаторы 'Lvl 2', определяющие твои основные ресурсы.",
        "data_source": "character_modifiers", # Подсказка сервису
        "items": {
            "hp_max": "Макс. Здоровье",
            "hp_regen": "Реген. Здоровья",
            "energy_max": "Макс. Энергия",
            "energy_regen": "Реген. Энергии",
        }
    },

    "physical_offense": {
        "title": "⚔️ Физическая Атака (Lvl 2)",
        "description": "Модификаторы 'Lvl 2', отвечающие за нанесение физического урона.",
        "items": {
            "physical_damage_bonus": "Бонус физ. урона",
            "physical_penetration": "Физ. пробивание",
            "physical_crit_chance": "Шанс физ. крита",
            "physical_crit_power_float": "Множитель физ. крита",
        }
    },

    "magical_offense": {
        "title": "🔮 Магическая Атака (Lvl 2)",
        "description": "Модификаторы 'Lvl 2', отвечающие за нанесение магического урона.",
        "items": {
            "magical_damage_bonus": "Бонус маг. урона",
            "magical_penetration": "Маг. пробивание",
            "magical_crit_chance": "Шанс маг. крита",
            "magical_crit_power_float": "Множитель маг. крита",
            "spell_land_chance": "Шанс попадания заклинанием",
            "magical_accuracy": "Магическая точность",
        }
    },

    "defense": {
        "title": "🛡️ Защита (Lvl 2)",
        "description": "Модификаторы 'Lvl 2', отвечающие за твою выживаемость в бою.",
        "items": {
            "physical_resistance": "Физ. сопротивление",
            "magical_resistance": "Маг. сопротивление",
            "control_resistance": "Сопр. контролю",
            "shock_resistance": "Сопр. шоку",
            "debuff_avoidance": "Уклонение от дебаффов",
            "dodge_chance": "Шанс уклонения",
            "anti_dodge": "Анти-уклонение",
            "shield_block_chance": "Шанс блока щитом",
            "shield_block_power": "Сила блока щитом",
            "anti_physical_crit_chance": "Защита от физ. крита",
            "anti_magical_crit_chance": "Защита от маг. крита",
        }
    },

    "general_combat": {
        "title": "✨ Общие Боевые (Lvl 2)",
        "description": "Модификаторы 'Lvl 2', дающие различные боевые преимущества.",
        "items": {
            "counter_attack_chance": "Шанс контратаки",
            "pet_ally_power": "Сила питомцев/союзников",
            "vampiric_rage": "Вампиризм",
            "received_healing_bonus": "Бонус получ. исцеления",
            "parry_chance": "Шанс парирования",
        }
    },

    "utility": {
        "title": "💰 Экономика и Ремесло (Lvl 2)",
        "description": "Модификаторы 'Lvl 2', влияющие на небоевые аспекты игры.",
        "items": {
            "trade_discount": "Торговая скидка",
            "find_loot_chance": "Шанс найти добычу",
            "crafting_critical_chance": "Шанс крит. крафта",
            "crafting_success_chance": "Шанс успеха крафта",
            "skill_gain_bonus": "Бонус к опыту навыков",
            "inventory_slots_bonus": "Доп. слоты инвентаря",
        }
    },

    # === LEVEL 2 (Детали) ===
    # Описания для *каждого* ключа из "items" выше

    # --- Lvl 1 (из 'base_stats') ---
    "strength": {"title": "Сила", "description": "<b>Сила (Strength) [Lvl 1]</b>\n\n(Описание в разработке...)",  "items": None},
    "agility": {"title": "Ловкость", "description": "<b>Ловкость (Agility) [Lvl 1]</b>\n\n(Описание в разработке...)",  "items": None},
    "endurance": {"title": "Выносливость", "description": "<b>Выносливость (Endurance) [Lvl 1]</b>\n\n(Описание в разработке...)",  "items": None},
    "intelligence": {"title": "Интеллект", "description": "<b>Интеллект (Intelligence) [Lvl 1]</b>\n\n(Описание в разработке...)",  "items": None},
    "wisdom": {"title": "Мудрость", "description": "<b>Мудрость (Wisdom) [Lvl 1]</b>\n\n(Описание в разработке...)",  "items": None},
    "men": {"title": "Дух", "description": "<b>Дух (Men) [Lvl 1]</b>\n\n(Описание в разработке...)",  "items": None},
    "perception": {"title": "Восприятие", "description": "<b>Восприятие (Perception) [Lvl 1]</b>\n\n(Описание в разработке...)",  "items": None},
    "charisma": {"title": "Харизма", "description": "<b>Харизма (Charisma) [Lvl 1]</b>\n\n(Описание в разработке...)",  "items": None},
    "luck": {"title": "Удача", "description": "<b>Удача (Luck) [Lvl 1]</b>\n\n(Описание в разработке...)",  "items": None},

    # --- Lvl 2 (из 'resources') ---
    "hp_max": {"title": "Макс. Здоровье", "description": "<b>Макс. Здоровье [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "hp_regen": {"title": "Реген. Здоровья", "description": "<b>Реген. Здоровья [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "energy_max": {"title": "Макс. Энергия", "description": "<b>Макс. Энергия [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "energy_regen": {"title": "Реген. Энергии", "description": "<b>Реген. Энергии [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},

    # --- Lvl 2 (из 'physical_offense') ---
    "physical_damage_bonus": {"title": "Бонус физ. урона", "description": "<b>Бонус физ. урона [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "physical_penetration": {"title": "Физ. пробивание", "description": "<b>Физ. пробивание [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "physical_crit_chance": {"title": "Шанс физ. крита", "description": "<b>Шанс физ. крита [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "physical_crit_power_float": {"title": "Множитель физ. крита", "description": "<b>Множитель физ. крита [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},

    # --- Lvl 2 (из 'magical_offense') ---
    "magical_damage_bonus": {"title": "Бонус маг. урона", "description": "<b>Бонус маг. урона [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "magical_penetration": {"title": "Маг. пробивание", "description": "<b>Маг. пробивание [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "magical_crit_chance": {"title": "Шанс маг. крита", "description": "<b>Шанс маг. крита [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "magical_crit_power_float": {"title": "Множитель маг. крита", "description": "<b>Множитель маг. крита [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "spell_land_chance": {"title": "Шанс попадания заклинанием", "description": "<b>Шанс попадания заклинанием [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "magical_accuracy": {"title": "Магическая точность", "description": "<b>Магическая точность [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},

    # --- Lvl 2 (из 'defense') ---
    "physical_resistance": {"title": "Физ. сопротивление", "description": "<b>Физ. сопротивление [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "magical_resistance": {"title": "Маг. сопротивление", "description": "<b>Маг. сопротивление [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "control_resistance": {"title": "Сопр. контролю", "description": "<b>Сопр. контролю [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "shock_resistance": {"title": "Сопр. шоку", "description": "<b>Сопр. шоку [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "debuff_avoidance": {"title": "Уклонение от дебаффов", "description": "<b>Уклонение от дебаффов [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "dodge_chance": {"title": "Шанс уклонения", "description": "<b>Шанс уклонения [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "anti_dodge": {"title": "Анти-уклонение", "description": "<b>Анти-уклонение [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "shield_block_chance": {"title": "Шанс блока щитом", "description": "<b>Шанс блока щитом [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "shield_block_power": {"title": "Сила блока щитом", "description": "<b>Сила блока щитом [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "anti_physical_crit_chance": {"title": "Защита от физ. крита", "description": "<b>Защита от физ. крита [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "anti_magical_crit_chance": {"title": "Защита от маг. крита", "description": "<b>Защита от маг. крита [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},

    # --- Lvl 2 (из 'general_combat') ---
    "counter_attack_chance": {"title": "Шанс контратаки", "description": "<b>Шанс контратаки [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "pet_ally_power": {"title": "Сила питомцев/союзников", "description": "<b>Сила питомцев/союзников [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "vampiric_rage": {"title": "Вампиризм", "description": "<b>Вампиризм [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "received_healing_bonus": {"title": "Бонус получ. исцеления", "description": "<b>Бонус получ. исцеления [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "parry_chance": {"title": "Шанс парирования", "description": "<b>Шанс парирования [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},

    # --- Lvl 2 (из 'utility') ---
    "trade_discount": {"title": "Торговая скидка", "description": "<b>Торговая скидка [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "find_loot_chance": {"title": "Шанс найти добычу", "description": "<b>Шанс найти добычу [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "crafting_critical_chance": {"title": "Шанс крит. крафта", "description": "<b>Шанс крит. крафта [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "crafting_success_chance": {"title": "Шанс успеха крафта", "description": "<b>Шанс успеха крафта [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "skill_gain_bonus": {"title": "Бонус к опыту навыков", "description": "<b>Бонус к опыту навыков [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
    "inventory_slots_bonus": {"title": "Доп. слоты инвентаря", "description": "<b>Доп. слоты инвентаря [Lvl 2]</b>\n\n(Описание в разработке...)", "data_source": "character_modifiers", "items": None},
}