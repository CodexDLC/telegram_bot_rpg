"""
FSM States для Telegram Bot.
Определяет состояния конечного автомата для навигации по игровым доменам.
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


# --- Configuration Lists ---

# Список состояний, где текстовые сообщения от юзера считаются мусором (удаляются)
GARBAGE_TEXT_STATES = [
    BotState.exploration,
    BotState.inventory,
    BotState.combat,
    BotState.status,
    BotState.arena,
    BotState.onboarding,
]
