from enum import StrEnum


class GameState(StrEnum):
    """
    Единый перечень состояний игрового цикла (экранов).
    Используется для синхронизации значений в Redis (поле 'state') и FSM.
    """

    EXPLORATION = "exploration"  # Основной режим: навигация, хабы, мир
    INVENTORY = "inventory"  # Меню инвентаря
    COMBAT = "combats"  # Активный бой
    SCENARIO = "scenario"  # Режим диалога/квеста
    STATUS = "status"  # Меню персонажа
    ONBOARDING = "onboarding"  # Создание персонажа / Туториал
    ARENA = "arena"  # Лобби арены (поиск матча)
    LOBBY = "lobby"  # Главное меню выбора персонажа


class CoreDomain(StrEnum):
    """
    Перечень всех доменов (оркестраторов) системы.
    Включает в себя как игровые стейты (GameState), так и служебные сервисы.
    Используется в CoreRouter для маршрутизации.
    """

    # --- Игровые домены (совпадают с GameState) ---
    EXPLORATION = "exploration"
    INVENTORY = "inventory"
    COMBAT = "combats"  # Обычно это CombatTurnOrchestrator
    SCENARIO = "scenario"
    ONBOARDING = "onboarding"
    LOBBY = "lobby"

    # --- Служебные / Специфичные домены ---
    COMBAT_ENTRY = "combat_entry"  # Вход в бой, создание сессии
    COMBAT_INTERACTION = "combat_interaction"  # Мгновенные действия и чтение
    CONTEXT_ASSEMBLER = "context_assembler"  # Сборка данных из БД в Redis
