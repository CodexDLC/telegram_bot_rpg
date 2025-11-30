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


class NavigationCallback(CallbackData, prefix="nav"):
    """
    Callback для перемещения и взаимодействия в мире.
    action: 'move' (переход), 'look' (осмотр) и т.д.
    target_id: ID локации (куда идем) или объекта.
    """

    action: str
    target_id: str


class ServiceEntryCallback(CallbackData, prefix="svc_entry"):
    """
    Callback для перехода из режима Навигации в Сервисный Контейнер (Арена, Таверна).
    """

    char_id: int
    target_loc: str  # ID локации, в которую заходим ('svc_arena_main')


class ArenaQueueCallback(CallbackData, prefix="arena"):
    """
    Callback для управления меню Арены и процессом подачи заявки/ожидания.
    """

    char_id: int
    # action: 'menu_main', 'submit_1v1', 'view_queue', 'cancel_queue', 'exit_service'
    action: str
    match_type: str = "none"
    match_id: str | None = None
