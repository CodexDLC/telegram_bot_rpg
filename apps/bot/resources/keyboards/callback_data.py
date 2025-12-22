from aiogram.filters.callback_data import CallbackData


class LobbySelectionCallback(CallbackData, prefix="lobby"):
    action: str
    char_id: int | None = None


class MeinMenuCallback(CallbackData, prefix="menu"):
    action: str
    game_stage: str
    char_id: int


class EncounterCallback(CallbackData, prefix="enc"):
    action: str  # "attack", "bypass", "inspect"
    target_id: str


class NavigationCallback(CallbackData, prefix="nav"):
    action: str  # "move", "search", "look_around"
    target_id: str | None = None
    t: float | None = 0.0  # Время перехода


class ServiceEntryCallback(CallbackData, prefix="svc"):
    target_loc: str
    char_id: int


class ArenaQueueCallback(CallbackData, prefix="arena"):
    action: str  # "match_menu", "toggle_queue", "start_battle", "exit_service"
    char_id: int
    match_type: str | None = None  # "1v1", "group"


class TutorialQuestCallback(CallbackData, prefix="tut_quest"):
    phase: str
    branch: str
    value: str


class ScenarioCallback(CallbackData, prefix="sc"):
    """
    Универсальный колбэк для системы сценариев.
    """

    action: str  # "initialize", "step"
    quest_key: str | None = None  # Для инициализации
    action_id: str | None = None  # Для шага


class GenderCallback(CallbackData, prefix="gender"):
    action: str
    value: str


class OnboardingCallback(CallbackData, prefix="onb"):
    """
    Универсальный колбэк для процесса онбординга (создания персонажа).
    """

    action: str  # "start", "set_gender", "finalize", etc.
    value: str | None = None
