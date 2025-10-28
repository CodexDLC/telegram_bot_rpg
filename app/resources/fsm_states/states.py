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



