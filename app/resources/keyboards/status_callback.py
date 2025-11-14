# app/resources/keyboards/status_callback.py

from aiogram.filters.callback_data import CallbackData


class StatusNavCallback(CallbackData, prefix="status_nav"):
    """
    Callback для *главного "таб-бара"* меню статуса (Уровень 0).
    Ловит только 'bio', 'stats', 'skills'.
    """
    char_id: int
    key: str  # 'bio', 'stats', 'skills'


class StatusSkillsCallback(CallbackData, prefix="skill_nav"):
    """
    Навигация ВНУТРИ вкладки "Навыки" (Уровень 1 и 2).
    """
    char_id: int
    level: str  # 'group' (список групп) или 'detail' (конкретный навык)
    key: str  # 'combat_base' или 'melee_combat'


class StatusModifierCallback(CallbackData, prefix="mod_nav"):
    """
    Навигация ВНУТРИ вкладки "Модификаторы" (Уровень 1 и 2).
    """
    char_id: int
    level: str  # 'group' (список групп) или 'detail' (конкретный стат)
    key: str  # 'base_stats' или 'strength'