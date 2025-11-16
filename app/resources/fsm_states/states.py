# app/resources/fsm_states/states.py
from aiogram.fsm.state import StatesGroup, State



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


FSM_CONTEX_CHARACTER_STATUS = [
    CharacterLobby.start_logging, CharacterLobby.selection, CharacterLobby.confirm_delete

]

GARBAGE_TEXT_STATES = [
    StartTutorial.start, StartTutorial.confirmation, StartTutorial.in_progress,
    StartTutorial.in_skills_progres, StartTutorial.skill_confirm,
    CharacterLobby.selection, CharacterLobby.start_logging, CharacterLobby.confirm_delete,
    CharacterCreation.choosing_gender, CharacterCreation.confirm
]