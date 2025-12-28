from typing import Any

from aiogram.types import User
from loguru import logger as log

from apps.bot.core_client.lobby_client import LobbyClient
from apps.bot.ui_service.base_bot_orchestrator import BaseBotOrchestrator
from apps.bot.ui_service.dto.view_dto import UnifiedViewDTO
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO
from apps.bot.ui_service.lobby.lobby_service import LobbyService
from apps.common.schemas_dto.game_state_enum import GameState
from apps.common.schemas_dto.lobby_dto import LobbyInitDTO


class LobbyBotOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор лобби на стороне бота.
    """

    def __init__(self, lobby_client: LobbyClient):
        # Ожидаем стейт LOBBY
        super().__init__(expected_state=GameState.LOBBY)
        self._client = lobby_client

    async def process_entry_point(self, user: User) -> Any:
        """
        Точка входа в состояние LOBBY.
        """
        # 1. Запрос к бэкенду
        response = await self._client.get_initial_lobby_state(user.id)

        # 2. Проверка на смену стейта (передаем user как fallback)
        if result := await self.check_and_switch_state(response, fallback_payload=user):
            return result

        # 3. Если стейт наш (LOBBY), рендерим UI
        if not response.payload:
            log.warning("LobbyBotOrchestrator | Empty payload from backend")
            return None

        if not isinstance(response.payload, LobbyInitDTO):
            log.error(f"LobbyBotOrchestrator | Invalid payload type: {type(response.payload)}")
            return None

        return await self._render_lobby(user, response.payload, char_id=None)

    async def render(self, payload: Any) -> UnifiedViewDTO:
        """
        Стандартный метод render (используется Директором при входе).
        """
        if isinstance(payload, User):
            return await self.process_entry_point(payload)
        if isinstance(payload, LobbyInitDTO):
            # Если нам передали сразу DTO, нам все равно нужен User для контекста (имени и т.д.)
            # Но render обычно вызывается с payload перехода.
            # В данном случае лучше вызвать entry point, так как LobbyInitDTO не содержит User.
            raise NotImplementedError("Lobby render requires User context via process_entry_point")

        return await self.process_entry_point(payload)

    async def _render_lobby(self, user: User, data: LobbyInitDTO, char_id: int | None) -> UnifiedViewDTO:
        """
        Внутренний метод отрисовки.
        """
        ui = LobbyService(user=user, state_data={}, char_id=char_id)

        # MENU: Список персонажей (с галочкой, если char_id задан)
        menu_text, menu_kb = ui.get_data_lobby_start(data.characters)

        content_view = None

        # CONTENT: Статус (только если выбран персонаж)
        if char_id:
            # TODO: Запросить реальный статус у StatusClient
            status_text = f"📊 <b>Статус персонажа</b> (ID: {char_id})\n\nЗдесь будет статистика..."
            content_view = ViewResultDTO(text=status_text, kb=None)

        return UnifiedViewDTO(
            menu=ViewResultDTO(text=menu_text, kb=menu_kb),
            content=content_view,
            clean_history=(char_id is None),  # Чистим историю только при первом входе (без выбора)
        )

    async def handle_create_character(self, user: User) -> Any:
        """
        Обрабатывает нажатие "Создать персонажа".
        """
        return await self.director.set_scene(GameState.ONBOARDING, payload=user)

    async def handle_select_character(self, user: User, char_id: int) -> UnifiedViewDTO:
        """
        Обрабатывает выбор персонажа.
        """
        # Получаем список персонажей
        characters = await self._client.get_characters(user.id)
        dto = LobbyInitDTO(characters=characters)

        # Рендерим лобби с выбранным ID
        return await self._render_lobby(user, dto, char_id=char_id)

    async def handle_enter_game(self, user: User, char_id: int) -> Any:
        """
        Обрабатывает нажатие "Войти".
        """
        # 1. Сохраняем сессию через Директора
        await self.director.set_char_id(char_id)

        # 2. Запрос к бэкенду
        response = await self._client.enter_game(user.id, char_id)

        # 3. Переключаем сцену (передаем user как fallback)
        if result := await self.check_and_switch_state(response, fallback_payload=user):
            return result

        # Если почему-то остались в лобби (ошибка?), рендерим лобби
        # Но сначала нужно получить актуальный DTO
        # Для простоты вернемся в entry point
        return await self.process_entry_point(user)

    async def handle_delete_request(self, user: User, char_id: int) -> UnifiedViewDTO:
        """
        Показывает подтверждение удаления.
        """
        ui = LobbyService(user=user, state_data={}, char_id=char_id)

        characters = await self._client.get_characters(user.id)
        char_name = "Персонаж"
        for char in characters:
            if char.character_id == char_id:
                char_name = char.name
                break

        text, kb = ui.get_message_delete(char_name)

        return UnifiedViewDTO(
            content=ViewResultDTO(text=text, kb=kb),
            menu=None,
            clean_history=False,
        )

    async def handle_delete_confirm(self, user: User, char_id: int) -> Any:
        """
        Удаляет персонажа и возвращает в список.
        """
        await self._client.delete_character(user.id, char_id)
        return await self.process_entry_point(user)
