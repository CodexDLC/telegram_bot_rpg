from typing import TYPE_CHECKING

from apps.common.schemas_dto.core_response_dto import CoreResponseDTO
from apps.common.schemas_dto.lobby_dto import LobbyInitDTO

if TYPE_CHECKING:
    from apps.game_core.core_container import CoreContainer


class LobbyClient:
    """
    Клиент для взаимодействия с LobbyCoreOrchestrator.
    """

    def __init__(self, core_container: "CoreContainer"):
        self.core = core_container

    async def get_initial_lobby_state(self, user_id: int) -> CoreResponseDTO[LobbyInitDTO]:
        """
        Запрашивает начальное состояние лобби.
        """
        async with self.core.get_session_context() as session:
            orchestrator = self.core.get_lobby_core_orchestrator(session)
            return await orchestrator.initialize_session(user_id)

    async def get_characters(self, user_id: int) -> list:
        """
        Получает список персонажей.
        """
        async with self.core.get_session_context() as session:
            orchestrator = self.core.get_lobby_core_orchestrator(session)
            response = await orchestrator.initialize_session(user_id)
            if response.payload:
                return response.payload.characters
            return []

    async def enter_game(self, user_id: int, char_id: int) -> CoreResponseDTO:
        """
        Вход в игру выбранным персонажем.
        """
        async with self.core.get_session_context() as session:
            orchestrator = self.core.get_lobby_core_orchestrator(session)
            return await orchestrator.enter_game(user_id, char_id)

    async def delete_character(self, user_id: int, char_id: int) -> None:
        """
        Удаление персонажа.
        """
        async with self.core.get_session_context() as session:
            orchestrator = self.core.get_lobby_core_orchestrator(session)
            await orchestrator.delete_character(user_id, char_id)
