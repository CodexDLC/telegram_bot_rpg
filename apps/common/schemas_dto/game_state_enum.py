from enum import StrEnum


class GameState(StrEnum):
    """
    Единый перечень состояний игрового цикла.
    Используется для синхронизации значений в Redis (поле 'state') и FSM.
    """

    EXPLORATION = "exploration"  # Основной режим: навигация, хабы, мир
    INVENTORY = "inventory"  # Меню инвентаря
    COMBAT = "combat"  # Активный бой
    SCENARIO = "scenario"  # Режим диалога/квеста
    STATUS = "status"  # Меню персонажа
    ONBOARDING = "onboarding"  # Создание персонажа / Туториал
    ARENA = "arena"  # Лобби арены (поиск матча)
    LOBBY = "lobby"  # Главное меню выбора персонажа
