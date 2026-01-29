from aiogram.filters.callback_data import CallbackData


class MeinMenuCallback(CallbackData, prefix="menu"):
    action: str
    game_stage: str
    char_id: int


class SystemCallback(CallbackData, prefix="sys"):
    """
    Универсальный колбэк для системных действий (Logout, Reset, etc).
    """

    action: str  # "logout", "main_menu"


class EncounterCallback(CallbackData, prefix="enc"):
    action: str  # "attack", "bypass", "inspect"
    target_id: str


class NavigationCallback(CallbackData, prefix="nav"):
    action: str  # "move", "search", "look_around"
    target_id: str | None = None
    t: float | None = 0.0  # Время перехода


class ArenaQueueCallback(CallbackData, prefix="arena"):
    action: str  # "match_menu", "toggle_queue", "start_battle", "exit_service"
    char_id: int
    match_type: str | None = None  # "1v1", "group"
