from aiogram.types import User

from apps.bot.core_client.lobby_client import LobbyClient
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import MessageCoordsDTO, ViewResultDTO
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.lobby.dto.lobby_view_dto import LobbyViewDTO
from apps.bot.ui_service.lobby.lobby_service import LobbyService
from apps.common.schemas_dto import CharacterReadDTO


class LobbyBotOrchestrator:
    """
    Оркестратор лобби на стороне бота.
    """

    def __init__(self, lobby_client: LobbyClient):
        self._client = lobby_client

    def _get_ui(self, user: User, state_data: dict, char_id: int | None = None) -> LobbyService:
        """Внутренняя фабрика для UI сервиса."""
        return LobbyService(user=user, state_data=state_data, char_id=char_id)

    def get_content_coords(self, state_data: dict) -> MessageCoordsDTO | None:
        """Возвращает координаты сообщения из FSM."""
        session_context = state_data.get(FSM_CONTEXT_KEY, {})
        content = session_context.get("message_content", {})
        if content:
            return MessageCoordsDTO(chat_id=content["chat_id"], message_id=content["message_id"])
        return None

    def get_menu_coords(self, state_data: dict) -> MessageCoordsDTO | None:
        """Возвращает координаты меню из FSM."""
        session_context = state_data.get(FSM_CONTEXT_KEY, {})
        menu = session_context.get("message_menu", {})
        if menu:
            return MessageCoordsDTO(chat_id=menu["chat_id"], message_id=menu["message_id"])
        return None

    async def get_lobby_view(self, user: User, state_data: dict, char_id: int | None = None) -> LobbyViewDTO:
        """Возвращает вид лобби (список персонажей)."""
        ui = self._get_ui(user, state_data, char_id)

        characters = await self._client.get_characters(user.id)
        text, kb = ui.get_data_lobby_start(characters)

        return LobbyViewDTO(content=ViewResultDTO(text=text, kb=kb))

    async def get_delete_confirmation(self, user: User, state_data: dict, char_id: int) -> LobbyViewDTO:
        """Возвращает экран подтверждения удаления."""
        ui = self._get_ui(user, state_data, char_id)

        characters = await self._client.get_characters(user.id)
        char_name = "Персонаж"
        for char in characters:
            if char.character_id == char_id:
                char_name = char.name
                break

        text, kb = ui.get_message_delete(char_name)
        return LobbyViewDTO(content=ViewResultDTO(text=text, kb=kb))

    async def create_character(self, user: User) -> LobbyViewDTO:
        """Создает персонажа и возвращает ID."""
        char_id = await self._client.create_character(user.id)
        return LobbyViewDTO(new_char_id=char_id)

    async def delete_character(self, char_id: int) -> LobbyViewDTO:
        """Удаляет персонажа."""
        success = await self._client.delete_character(char_id)
        return LobbyViewDTO(is_deleted=success)

    async def get_user_characters(self, user_id: int) -> list[CharacterReadDTO]:
        """Возвращает список персонажей пользователя."""
        return await self._client.get_characters(user_id)
