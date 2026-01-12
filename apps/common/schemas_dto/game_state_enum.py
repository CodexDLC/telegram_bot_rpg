from enum import StrEnum


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
