# app/resources/keyboards/callback_data.py


from aiogram.filters.callback_data import CallbackData


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
    char_id: int | None = None


class TutorialQuestCallback(CallbackData, prefix="tut_quest"):
    """
    Управляет навигацией по всему FSM-квесту создания персонажа.

    """

    branch: str
    phase: str
    value: str
