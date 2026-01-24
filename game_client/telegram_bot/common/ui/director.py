from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from aiogram.fsm.context import FSMContext
from loguru import logger

from game_client.telegram_bot.common.ui.registry import DIRECTOR_ROUTES

# Константа для ключа FSM State (хранит данные игровой сессии)
KEY_SESSION_DATA = "session_data"

if TYPE_CHECKING:
    from game_client.telegram_bot.core.container import BotContainer


# Протокол только для проверки наличия методов, без жесткого DTO
@runtime_checkable
class UIOrchestratorProtocol(Protocol):
    async def render(self, payload: Any) -> Any: ...
    def set_director(self, director: Any): ...


class GameDirector:
    def __init__(self, container: "BotContainer", state: FSMContext):
        self.container = container
        self.state = state

    async def set_scene(self, target_state: str, payload: Any) -> Any:
        """
        Переключает сцену и возвращает ViewDTO нового режима.
        """
        scene_config = DIRECTOR_ROUTES.get(target_state)

        if not scene_config:
            logger.error(f"Director: Unknown scene '{target_state}'")
            return None

        # 1. Смена FSM
        current_fsm = await self.state.get_state()
        if current_fsm != scene_config.fsm_state.state:
            await self.state.set_state(scene_config.fsm_state)

        # 2. Получение Оркестратора из BotContainer
        factory_method = getattr(self.container, scene_config.container_getter, None)
        if not factory_method:
            logger.error(f"Director: Container missing '{scene_config.container_getter}'")
            return None

        # Вызываем фабрику (без аргументов)
        orchestrator = factory_method()

        # 3. Внедрение зависимости (Setter Injection)
        if hasattr(orchestrator, "set_director"):
            orchestrator.set_director(self)

        # 4. Рендер
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
