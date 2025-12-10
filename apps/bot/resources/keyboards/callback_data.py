"""
Модуль содержит определения CallbackData для различных интерактивных элементов.

Каждый класс `CallbackData` определяет структуру данных,
которая будет передаваться при нажатии на Inline-кнопки,
обеспечивая типизированный и безопасный способ обработки
действий пользователя.
"""

from aiogram.filters.callback_data import CallbackData


class MeinMenuCallback(CallbackData, prefix="menu"):
    """
    Callback для главного меню.

    Attributes:
        action: Какое действие должно быть выполнено (например, "status", "inventory").
        game_stage: Текущая стадия игры, определяющая доступные кнопки.
        char_id: Идентификатор персонажа.
    """

    action: str
    game_stage: str
    char_id: int


class LobbySelectionCallback(CallbackData, prefix="lsc"):
    """
    Callback для выбора/создания персонажа в лобби.

    Attributes:
        action: Действие ("select", "create", "login", "logout").
        char_id: Идентификатор персонажа (опционально, не требуется для "create").
    """

    action: str
    char_id: int | None = None


class TutorialQuestCallback(CallbackData, prefix="tut_quest"):
    """
    Callback для управления навигацией по FSM-квесту туториала.

    Attributes:
        branch: Ветка квеста (например, "path_melee").
        phase: Фаза квеста (например, "step_1", "finale").
        value: Выбранное значение или действие.
    """

    branch: str
    phase: str
    value: str


class NavigationCallback(CallbackData, prefix="nav"):
    """
    Callback для перемещения и взаимодействия в игровом мире.

    Attributes:
        action: Действие ("move", "look" и т.д.).
        target_id: Идентификатор целевой локации или объекта.
    """

    action: str
    target_id: str


class ServiceEntryCallback(CallbackData, prefix="svc_entry"):
    """
    Callback для перехода из режима Навигации в Сервисный Контейнер (например, Арена, Таверна).

    Attributes:
        char_id: Идентификатор персонажа.
        target_loc: Идентификатор целевой локации/сервиса (например, 'svc_arena_main').
    """

    char_id: int
    target_loc: str


class ArenaQueueCallback(CallbackData, prefix="arena"):
    """
    Callback для управления меню Арены и процессом подачи заявки/ожидания.

    Attributes:
        char_id: Идентификатор персонажа.
        action: Действие (например, "menu_main", "submit_1v1", "cancel_queue").
        match_type: Тип матча (например, "1v1", "group").
        match_id: Идентификатор матча (опционально).
    """

    char_id: int
    action: str
    match_type: str = "none"
    match_id: str | None = None
