"""
Модуль содержит определения состояний FSM (Finite State Machine) для бота.

Каждый класс `StatesGroup` инкапсулирует набор состояний,
соответствующих определенному этапу взаимодействия пользователя с ботом
(например, создание персонажа, прохождение туториала, игровой процесс).
"""

from aiogram.fsm.state import State, StatesGroup


class CharacterCreation(StatesGroup):
    """Состояния для "квеста" создания персонажа."""

    choosing_gender = State()
    choosing_name = State()
    confirm = State()


class StartTutorial(StatesGroup):
    """Состояния для "квеста" старта туториала."""

    start = State()
    in_progress = State()
    confirmation = State()
    in_skills_progres = State()
    skill_confirm = State()


class CharacterLobby(StatesGroup):
    """Состояния для лобби персонажей."""

    selection = State()
    start_logging = State()
    confirm_delete = State()


class BugReport(StatesGroup):
    """Состояния для процесса отправки баг-репорта."""

    choosing_type = State()
    awaiting_report_text = State()


class InGame(StatesGroup):
    """Состояния, когда игрок находится в игровом мире."""

    lobby = State()
    onboarding = State()  # <-- Новый этап: создание "Био"
    exploration = State()  # <-- Бывший navigation
    inventory = State()
    combat = State()
    status = State()
    scenario = State()
    arena = State()


class AdminMode(StatesGroup):
    """Состояния для админ-панели."""

    menu = State()
    item_creation = State()
    resource_add = State()
    teleport = State()


class ArenaState(StatesGroup):
    """Состояния для Арены (Legacy, будет заменено на InGame.arena)."""

    menu = State()
    waiting = State()


# ЛЕЧИЛКА: Расширенный список состояний, в которых разрешена работа меню Статуса (2 и 3 уровни вложенности)
FSM_CONTEX_CHARACTER_STATUS = [
    # Лобби
    CharacterLobby.start_logging,
    CharacterLobby.selection,
    CharacterLobby.confirm_delete,
    # Основной игровой цикл
    InGame.exploration,  # <-- Обновлено
    InGame.inventory,
    InGame.combat,
    InGame.status,
    InGame.scenario,
    InGame.arena,
    # Арена (Legacy)
    ArenaState.menu,
    ArenaState.waiting,
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
