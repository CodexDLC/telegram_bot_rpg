# apps/bot/ui_service/game_director/director.py
from typing import Any, Protocol, runtime_checkable

from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.ui_service.game_director.registry import DIRECTOR_ROUTES
from apps.common.core.container import AppContainer


# Протокол только для проверки наличия методов, без жесткого DTO
@runtime_checkable
class UIOrchestratorProtocol(Protocol):
    async def render(self, payload: Any) -> Any: ...
    def set_director(self, director: Any): ...


class GameDirector:
    def __init__(self, container: AppContainer, state: FSMContext, session: AsyncSession):
        self.container = container
        self.state = state
        self.session = session

    async def set_scene(self, target_state: str, payload: Any) -> Any:
        """
        Переключает сцену и возвращает ViewDTO нового режима.
        Тип возврата Any, потому что это может быть CombatViewDTO или ScenarioViewDTO.
        """
        scene_config = DIRECTOR_ROUTES.get(target_state)

        if not scene_config:
            logger.error(f"Director: Unknown scene '{target_state}'")
            return None  # Или базовый ErrorDTO

        # 1. Смена FSM
        current_fsm = await self.state.get_state()
        if current_fsm != scene_config.fsm_state.state:
            await self.state.set_state(scene_config.fsm_state)

        # 2. Получение Оркестратора
        factory_method = getattr(self.container, scene_config.container_getter, None)
        if not factory_method:
            logger.error(f"Director: Container missing '{scene_config.container_getter}'")
            return None

        orchestrator = factory_method(self.session)

        # 3. Внедрение зависимости (Setter Injection)
        if hasattr(orchestrator, "set_director"):
            orchestrator.set_director(self)

        # 4. Рендер
        if not hasattr(orchestrator, "render"):
            logger.error(f"Director: {type(orchestrator)} missing 'render'")
            return None

        # Возвращаем специфичный DTO (например, CombatViewDTO)
        return await orchestrator.render(payload)
