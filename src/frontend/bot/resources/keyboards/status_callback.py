"""
Модуль содержит определения CallbackData для навигации по меню статуса персонажа.

Определяет структуры данных для кнопок переключения вкладок (био, навыки, модификаторы),
навигации внутри вкладок (группы навыков, детали модификаторов)
и изменения режима прокачки навыков.
"""

from aiogram.filters.callback_data import CallbackData


class StatusNavCallback(CallbackData, prefix="status_nav"):
    """
    Callback для главного "таб-бара" меню статуса (Уровень 0).

    Attributes:
        char_id: Идентификатор персонажа.
        key: Ключ вкладки ('bio', 'stats', 'skills').
    """

    char_id: int
    key: str


class StatusSkillsCallback(CallbackData, prefix="skill_nav"):
    """
    Callback для навигации внутри вкладки "Навыки" (Уровень 1 и 2).

    Attributes:
        char_id: Идентификатор персонажа.
        level: Уровень навигации ('group' для списка групп, 'detail' для конкретного навыка).
        key: Ключ группы навыков или конкретного навыка.
    """

    char_id: int
    level: str
    key: str


class StatusModifierCallback(CallbackData, prefix="mod_nav"):
    """
    Callback для навигации внутри вкладки "Модификаторы" (Уровень 1 и 2).

    Attributes:
        char_id: Идентификатор персонажа.
        level: Уровень навигации ('group' для списка групп, 'detail' для конкретного стата).
        key: Ключ группы модификаторов или конкретного модификатора.
    """

    char_id: int
    level: str
    key: str


class SkillModeCallback(CallbackData, prefix="skill_mode"):
    """
    Callback для изменения режима прокачки навыка.

    Attributes:
        char_id: Идентификатор персонажа.
        skill_key: Ключ навыка, режим которого изменяется.
        new_mode: Новый режим ('PLUS', 'PAUSE' или 'MINUS').
    """

    char_id: int
    skill_key: str
    new_mode: str
