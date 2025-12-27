from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto import CharacterReadDTO
from apps.common.schemas_dto.core_response_dto import CoreResponseDTO
from apps.common.schemas_dto.lobby_dto import LobbyInitDTO
from apps.common.services.core_service.redis_service import RedisService
from apps.game_core.game_service.lobby.lobby_orchestrator import LobbyCoreOrchestrator


class LobbyClient:
    """
    Клиент для взаимодействия с системой лобби.
    """

    def __init__(self, session: AsyncSession, redis_service: RedisService):
        self._orchestrator = LobbyCoreOrchestrator(session, redis_service)

    async def get_initial_lobby_state(self, user_id: int) -> CoreResponseDTO[LobbyInitDTO]:
        """
        Запрашивает начальное состояние лобби (Onboarding или Список персонажей).
        """
        return await self._orchestrator.initialize_session(user_id)

    async def enter_game(self, user_id: int, char_id: int) -> CoreResponseDTO[None]:
        """
        Запрашивает вход в игру для выбранного персонажа.
        Возвращает целевой GameState.
        """
        return await self._orchestrator.enter_game(user_id, char_id)

    async def get_characters(self, user_id: int) -> list[CharacterReadDTO]:
        return await self._orchestrator.get_user_characters(user_id)

    async def create_character(self, user_id: int) -> int:
        return await self._orchestrator.create_character_shell(user_id)

    async def delete_character(self, user_id: int, char_id: int) -> bool:
        return await self._orchestrator.delete_character(user_id, char_id)
