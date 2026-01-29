from aiogram.types import User

from src.frontend.telegram_bot.base.base_orchestrator import BaseBotOrchestrator
from src.frontend.telegram_bot.base.view_dto import UnifiedViewDTO
from src.frontend.telegram_bot.features.account.client import AccountClient
from src.frontend.telegram_bot.features.account.system.lobby_ui import LobbyUI
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.lobby import LobbyListDTO


class LobbyOrchestrator(BaseBotOrchestrator):
    def __init__(self, client: AccountClient):
        super().__init__(expected_state=CoreDomain.LOBBY)
        self.client = client
        self.ui = LobbyUI()

    async def render(self, payload) -> UnifiedViewDTO:
        """
        Entry point от Director при переходе в LOBBY.
        """
        if isinstance(payload, User):
            return await self.handle_lobby_initialize(payload)

        if isinstance(payload, LobbyListDTO):
            return self._render_lobby(payload.characters, selected_char_id=None)

        return await self.handle_lobby_initialize(payload)

    async def handle_lobby_initialize(self, user: User) -> UnifiedViewDTO:
        """
        Первый вход в лобби (adventure callback).
        """
        response = await self.client.initialize_lobby(user.id)

        switch_result = await self.check_and_switch_state(response, fallback_payload=user)
        if switch_result:
            return switch_result

        if not response.payload:
            return UnifiedViewDTO()

        characters = response.payload.characters if hasattr(response.payload, "characters") else []
        return self._render_lobby(characters, selected_char_id=None)

    async def handle_character_select(self, user: User, char_id: int) -> UnifiedViewDTO:
        """
        Выбор персонажа — показать карточку.
        """
        response = await self.client.get_characters(user.id)

        if not response.payload:
            return UnifiedViewDTO()

        characters = response.payload.characters
        selected_char = None
        for char in characters:
            if char.character_id == char_id:
                selected_char = char
                break

        menu_view = self.ui.render_lobby_menu(characters, selected_char_id=char_id)
        content_view = self.ui.render_character_card(selected_char) if selected_char else None

        return UnifiedViewDTO(menu=menu_view, content=content_view)

    async def handle_character_login(self, user: User, char_id: int) -> UnifiedViewDTO:
        """
        Вход в игру выбранным персонажем.
        """
        await self.director.set_char_id(char_id)

        response = await self.client.login(user.id, char_id)

        switch_result = await self.check_and_switch_state(response, fallback_payload=user)
        if switch_result:
            return switch_result

        return await self.handle_lobby_initialize(user)

    async def handle_character_create(self, user: User) -> UnifiedViewDTO:
        """
        Создание нового персонажа — переход в онбординг.
        """
        response = await self.client.create_character(user.id)

        switch_result = await self.check_and_switch_state(response, fallback_payload=user)
        if switch_result:
            return switch_result

        return await self.handle_lobby_initialize(user)

    async def handle_delete_request(self, user: User, char_id: int) -> UnifiedViewDTO:
        """
        Запрос на удаление — показать подтверждение.
        """
        response = await self.client.get_characters(user.id)

        if not response.payload:
            return UnifiedViewDTO()

        characters = response.payload.characters
        char_name = "Персонаж"
        for char in characters:
            if char.character_id == char_id:
                char_name = char.name
                break

        menu_view = self.ui.render_delete_confirm(char_name, char_id)
        return UnifiedViewDTO(menu=menu_view, content=None)

    async def handle_delete_confirm(self, user: User, char_id: int) -> UnifiedViewDTO:
        """
        Подтверждение удаления — удалить и обновить список.
        """
        response = await self.client.delete_character(char_id, user.id)

        if not response.payload:
            return await self.handle_lobby_initialize(user)

        characters = response.payload.characters
        return self._render_lobby(characters, selected_char_id=None)

    def _render_lobby(self, characters: list, selected_char_id: int | None) -> UnifiedViewDTO:
        """
        Внутренний метод рендера лобби.
        """
        menu_view = self.ui.render_lobby_menu(characters, selected_char_id)
        return UnifiedViewDTO(menu=menu_view, content=None)
