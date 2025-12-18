# apps/bot/resources/keyboards/callback_data.py
from aiogram.filters.callback_data import CallbackData


class MeinMenuCallback(CallbackData, prefix="menu"):
    action: str
    game_stage: str
    char_id: int


class LobbySelectionCallback(CallbackData, prefix="lsc"):
    action: str
    char_id: int | None = None


class TutorialQuestCallback(CallbackData, prefix="tut_quest"):
    branch: str
    phase: str
    value: str


class NavigationCallback(CallbackData, prefix="nav"):
    action: str
    target_id: str
    t: float = 0.0


class ServiceEntryCallback(CallbackData, prefix="svc_entry"):
    char_id: int
    target_loc: str


class ArenaQueueCallback(CallbackData, prefix="arena"):
    char_id: int
    action: str
    match_type: str = "none"
    match_id: str | None = None


class GenderCallback(CallbackData, prefix="gender"):
    value: str


class EncounterCallback(CallbackData, prefix="enc"):
    """
    Callback для взаимодействия с энкаунтером.
    Attributes:
        action: "attack", "bypass" (обойти), "inspect" (нарратив).
        target_id: ID энкаунтера (моба или события).
    """

    action: str
    target_id: str
