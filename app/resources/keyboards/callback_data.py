# app/resources/keyboards/callback_data.py

from typing import Optional

from aiogram.filters.callback_data import CallbackData


class StatusNavCallback(CallbackData, prefix="statnav"):
    """
    Универсальный иерархический коллбек для ВСЕЙ навигации по Меню Статуса.
    (Заменяет StatusMenuCallback и SkillMenuCallback)

    Args:
        char_id (int): ID персонажа
        level (int): Уровень вложенности:
                     0 = 'tab' (Уровень вкладок: 'bio', 'skills', 'stats')
                     1 = 'group' (Уровень групп: 'combat_base', 'base_stats')
                     2 = 'detail' (Уровень детализации: 'melee_combat', 'strength')
        key (str): Строковый ключ для идентификации на этом уровне
                   (e.g., 'bio', 'combat_base', 'melee_combat')
    """
    char_id: int
    level: int
    key: str


class MeinMenuCallback(CallbackData, prefix="menu"):
    """
    action:         Какую кнопку нажали какой обработчик вызвать
    game_stage:     Сколько кнопок доступно
    char_id:        ID персонажа
    """

    action: str
    game_stage: str
    char_id: int


class LobbySelectionCallback(CallbackData, prefix="lsc"):
    """
    Callback для выбора/создания персонажа в лобби.
    action: 'select', 'create', 'login', 'logout'
    char_id: ID персонажа (используется только для action='select')
    """
    action: str
    # Используем Optional, т.к. 'create' не требует ID
    char_id: Optional[int] = None


class TutorialQuestCallback(CallbackData, prefix="tut_quest"):
    """
    Управляет навигацией по всему FSM-квесту создания персонажа.

    """
    branch: str
    phase: str
    value: str