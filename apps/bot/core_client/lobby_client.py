from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto import CharacterReadDTO
from apps.game_core.game_service.lobby.lobby_orchestrator import LobbyCoreOrchestrator


class LobbyClient:
    """
    Клиент для взаимодействия с системой лобби.
    """

    def __init__(self, session: AsyncSession):
        self._orchestrator = LobbyCoreOrchestrator(session)

    async def get_characters(self, user_id: int) -> list[CharacterReadDTO]:
        return await self._orchestrator.get_user_characters(user_id)

    async def create_character(self, user_id: int) -> int:
        return await self._orchestrator.create_character_shell(user_id)

    async def delete_character(self, char_id: int) -> bool:
        return await self._orchestrator.delete_character(char_id)
