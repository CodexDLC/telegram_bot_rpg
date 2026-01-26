from typing import Annotated

from fastapi import Depends

# Import dependencies from domains
from backend.dependencies.features.combat import CombatEntryOrchestratorDep, CombatGatewayDep
from backend.dependencies.features.scenario import ScenarioGatewayDep
from backend.domains.internal_systems.dispatcher.system_dispatcher import SystemDispatcher
from common.schemas.enums import CoreDomain


async def get_system_dispatcher(
    combat_entry: CombatEntryOrchestratorDep,
    combat_gateway: CombatGatewayDep,
    scenario_gateway: ScenarioGatewayDep,
) -> SystemDispatcher:
    """
    Собирает SystemDispatcher и регистрирует в нем все доступные оркестраторы.
    """

    # 1. Создаем пустой диспетчер
    dispatcher = SystemDispatcher()

    # 2. Combat Entry (Создание боя)
    # Теперь это полноценная зависимость, собранная в combat.py
    dispatcher.register(CoreDomain.COMBAT_ENTRY, lambda: combat_entry)

    # 3. Combat Runtime (Сам бой - Gateway)
    dispatcher.register(CoreDomain.COMBAT, lambda: combat_gateway)

    # 4. Scenario (Квесты)
    dispatcher.register(CoreDomain.SCENARIO, lambda: scenario_gateway)

    # TODO: Register other domains (Lobby, Inventory, etc.)

    return dispatcher


SystemDispatcherDep = Annotated[SystemDispatcher, Depends(get_system_dispatcher)]
