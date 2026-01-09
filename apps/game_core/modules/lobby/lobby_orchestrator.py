from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto import CharacterReadDTO
from apps.common.schemas_dto.core_response_dto import CoreResponseDTO, GameStateHeader
from apps.common.schemas_dto.game_state_enum import GameState
from apps.common.schemas_dto.lobby_dto import LobbyInitDTO
from apps.common.services.redis.redis_service import RedisService
from apps.game_core.modules.lobby.lobby_session_manager import LobbySessionManager


class LobbyCoreOrchestrator:
    """
    Оркестратор лобби (Core Layer).
    Управляет бизнес-процессом входа в лобби.
    Не работает с БД/Redis напрямую, использует LobbySessionManager.
    """

    def __init__(self, session: AsyncSession, redis_service: RedisService):
        # Создаем менеджер, передавая ему зависимости
        self.manager = LobbySessionManager(session, redis_service)

    async def initialize_session(self, user_id: int) -> CoreResponseDTO[LobbyInitDTO]:
        """
        Инициализирует сессию лобби.
        Определяет, куда направить пользователя (Lobby или Onboarding).
        """
        # Получаем данные через менеджер (он сам решит, откуда брать: кэш или БД)
        characters = await self.manager.get_characters(user_id)

        # Логика ветвления (Бизнес-логика)
        if not characters:
            return CoreResponseDTO(header=GameStateHeader(current_state=GameState.ONBOARDING), payload=None)

        return CoreResponseDTO(
            header=GameStateHeader(current_state=GameState.LOBBY), payload=LobbyInitDTO(characters=characters)
        )

    async def enter_game(self, user_id: int, char_id: int) -> CoreResponseDTO[None]:
        """
        Обрабатывает вход в игру.
        Определяет, в каком состоянии должен оказаться персонаж.
        """
        # TODO: Здесь должна быть проверка активной сессии (ac:{char_id})
        # и определение реального стейта (Combat, Scenario, etc.)
        # Пока возвращаем дефолтный EXPLORATION.

        return CoreResponseDTO(header=GameStateHeader(current_state=GameState.EXPLORATION), payload=None)

    async def get_user_characters(self, user_id: int) -> list[CharacterReadDTO]:
        """
        Возвращает список персонажей.
        """
        return await self.manager.get_characters(user_id)

    async def create_character_shell(self, user_id: int) -> int:
        """
        Создает оболочку персонажа.
        """
        return await self.manager.create_character(user_id)

    async def delete_character(self, user_id: int, char_id: int) -> bool:
        """
        Удаляет персонажа.
        """
        return await self.manager.delete_character(user_id, char_id)
