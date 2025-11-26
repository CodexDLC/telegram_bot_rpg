# app/resources/fsm_states/states.py
from aiogram.fsm.state import State, StatesGroup


class CharacterCreation(StatesGroup):
    """
    Состояния для "квеста" создания персонажа.
    """

    choosing_gender = State()
    choosing_name = State()
    confirm = State()


class StartTutorial(StatesGroup):
    """
    Состояния для "квеста" старта туториала.
    """

    start = State()
    in_progress = State()
    confirmation = State()
    in_skills_progres = State()
    skill_confirm = State()


class CharacterLobby(StatesGroup):
    selection = State()
    start_logging = State()
    confirm_delete = State()


class BugReport(StatesGroup):
    choosing_type = State()
    awaiting_report_text = State()


class InGame(StatesGroup):
    """Состояния, когда игрок находится в игровом мире."""

    navigation = State()
    inventory = State()


class AdminMode(StatesGroup):
    """Состояния для админ-панели"""

    menu = State()

    # Состояния для инструментов
    item_creation = State()
    resource_add = State()
    teleport = State()


FSM_CONTEX_CHARACTER_STATUS = [
    CharacterLobby.start_logging,
    CharacterLobby.selection,
    CharacterLobby.confirm_delete,
    InGame.navigation,
]

GARBAGE_TEXT_STATES = [
    StartTutorial.start,
    StartTutorial.confirmation,
    StartTutorial.in_progress,
    StartTutorial.in_skills_progres,
    StartTutorial.skill_confirm,
    CharacterLobby.selection,
    CharacterLobby.start_logging,
    CharacterLobby.confirm_delete,
    CharacterCreation.choosing_gender,
    CharacterCreation.confirm,
]
