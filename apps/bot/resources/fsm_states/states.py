"""
Модуль содержит определения состояний FSM (Finite State Machine) для бота.

Каждый класс `StatesGroup` инкапсулирует набор состояний,
соответствующих определенному этапу взаимодействия пользователя с ботом.
"""

from aiogram.fsm.state import State, StatesGroup


class BotState(StatesGroup):
    """
    Единый контейнер состояний игрового процесса.
    Порядок отражает типичный путь игрока.
    """

    # 1. Вход и создание
    lobby = State()  # Техническое состояние перехода из Лобби
    onboarding = State()  # Создание персонажа (Био, Класс)

    # 2. Мир и Сюжет
    exploration = State()  # Навигация, Хабы, Перемещение
    scenario = State()  # Диалоги, Квесты, Туториал

    # 3. Активные режимы
    combat = State()  # Боевая система
    arena = State()  # PvP/PvE Арена

    # 4. Меню и Управление
    inventory = State()  # Инвентарь, Экипировка
    status = State()  # Профиль, Навыки, Статы


# --- Legacy / Deprecated (Кандидаты на удаление) ---


class CharacterCreation(StatesGroup):
    """[DEPRECATED] Заменено на InGame.onboarding"""

    choosing_gender = State()
    choosing_name = State()
    confirm = State()


class StartTutorial(StatesGroup):
    """[DEPRECATED] Заменено на InGame.scenario"""

    start = State()
    in_progress = State()
    confirmation = State()
    in_skills_progres = State()
    skill_confirm = State()


class ArenaState(StatesGroup):
    """[DEPRECATED] Заменено на InGame.arena"""

    menu = State()
    waiting = State()


# --- System States ---


class BugReport(StatesGroup):
    """Состояния для процесса отправки баг-репорта."""

    choosing_type = State()
    awaiting_report_text = State()


class AdminMode(StatesGroup):
    """Состояния для админ-панели."""

    menu = State()
    item_creation = State()
    resource_add = State()
    teleport = State()


# --- Configuration Lists ---

# Список состояний, в которых разрешена работа меню Статуса
FSM_CONTEX_CHARACTER_STATUS = [
    # Лобби
    # Основной игровой цикл (InGame)
    BotState.exploration,
    BotState.scenario,
    BotState.combat,
    BotState.arena,
    BotState.inventory,
    BotState.status,
    BotState.onboarding,
    # Legacy (пока не удалим код)
    ArenaState.menu,
    ArenaState.waiting,
]

# Список состояний, где текстовые сообщения от юзера считаются мусором (удаляются)
GARBAGE_TEXT_STATES = [
    # Лобби
    # InGame (где нет ввода текста)
    BotState.exploration,
    BotState.inventory,
    BotState.combat,
    BotState.status,
    BotState.arena,
    # Legacy
    StartTutorial.start,
    StartTutorial.in_progress,
    CharacterCreation.choosing_gender,
    CharacterCreation.confirm,
]
