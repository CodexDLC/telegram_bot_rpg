from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from aiogram.fsm.context import FSMContext
from loguru import logger

from src.frontend.telegram_bot.services.director.registry import RENDER_ROUTES, SCENE_ROUTES

# Константа для ключа FSM State (хранит данные игровой сессии)
KEY_SESSION_DATA = "session_data"

if TYPE_CHECKING:
    from src.frontend.telegram_bot.core.container import BotContainer


# Протокол только для проверки наличия методов, без жесткого DTO
@runtime_checkable
class UIOrchestratorProtocol(Protocol):
    async def render(self, payload: Any) -> Any: ...
    def set_director(self, director: Any): ...


class GameDirector:
    def __init__(self, container: "BotContainer", state: FSMContext):
        self.container = container
        self.state = state

    async def set_scene(self, feature: str, payload: Any) -> Any:
        """
        Межфичевый переход: смена FSM State + вызов entry service.

        Args:
            feature: Ключ фичи (CoreDomain.COMBAT, CoreDomain.EXPLORATION, etc.)
            payload: Данные для рендера

        Returns:
            ViewDTO от entry orchestrator
        """
        scene_config = SCENE_ROUTES.get(feature)

        if not scene_config:
            logger.error(f"Director: Unknown scene '{feature}'")
            return None

        # 1. Смена FSM State
        current_fsm = await self.state.get_state()
        if current_fsm != scene_config.fsm_state.state:
            await self.state.set_state(scene_config.fsm_state)
            logger.debug(f"Director: FSM changed to '{scene_config.fsm_state}'")

        # 2. Вызов entry service через render()
        return await self.render(feature, scene_config.entry_service, payload)

    async def render(self, feature: str, service: str, payload: Any) -> Any:
        """
        Внутрифичевый переход: вызов orchestrator БЕЗ смены FSM State.

        Args:
            feature: Ключ фичи (CoreDomain.COMBAT, CoreDomain.EXPLORATION, etc.)
            service: Ключ сервиса внутри фичи ("navigation", "interaction", etc.)
            payload: Данные для рендера

        Returns:
            ViewDTO от orchestrator
        """
        # 1. Поиск feature в RENDER_ROUTES
        feature_routes = RENDER_ROUTES.get(feature)
        if not feature_routes:
            logger.error(f"Director: Unknown feature '{feature}' in RENDER_ROUTES")
            return None

        # 2. Поиск service внутри feature
        container_getter = feature_routes.get(service)
        if not container_getter:
            logger.error(f"Director: Unknown service '{service}' in feature '{feature}'")
            return None

        # 3. Получение service из BotContainer
        factory_method = getattr(self.container, container_getter, None)
        if not factory_method:
            logger.error(f"Director: Container missing '{container_getter}'")
            return None

        orchestrator = factory_method()

        # 4. Setter Injection (Director -> service)
        if hasattr(orchestrator, "set_director"):
            orchestrator.set_director(self)

        # 5. Render
        if not hasattr(orchestrator, "render"):
            logger.error(f"Director: {type(orchestrator)} missing 'render'")
            return None

        return await orchestrator.render(payload)

    # --- Session Management ---

    async def set_char_id(self, char_id: int) -> None:
        """
        Сохраняет ID персонажа в сессию.
        """
        data = await self.state.get_data()
        session_data = data.get(KEY_SESSION_DATA, {})
        session_data["char_id"] = char_id
        await self.state.update_data({KEY_SESSION_DATA: session_data})
        logger.info(f"Director | action=set_char_id char_id={char_id}")

    async def get_char_id(self) -> int | None:
        """
        Возвращает ID текущего персонажа из сессии.
        """
        data = await self.state.get_data()
        session_data = data.get(KEY_SESSION_DATA, {})
        return session_data.get("char_id")

    async def clear_session(self) -> None:
        """
        Очищает данные сессии (выход из игры).
        """
        await self.state.update_data({KEY_SESSION_DATA: {}})
