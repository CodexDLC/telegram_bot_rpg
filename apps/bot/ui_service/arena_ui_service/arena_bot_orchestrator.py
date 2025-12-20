from apps.bot.core_client.arena_client import ArenaClient
from apps.bot.core_client.exploration import ExplorationClient
from apps.bot.ui_service.arena_ui_service.arena_ui_service import ArenaUIService
from apps.bot.ui_service.arena_ui_service.dto.arena_view_dto import ArenaViewDTO
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import MessageCoordsDTO, ViewResultDTO
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY


class ArenaBotOrchestratorError(Exception):
    """Ошибка в работе оркестратора арены."""

    pass


class ArenaBotOrchestrator:
    """
    Оркестратор на стороне бота.
    Связывает вызовы к "бэкенду" (через ArenaClient) с отрисовкой UI (через ArenaUIService).
    Предоставляет хендлерам готовые для отправки пользователю данные.
    """

    def __init__(self, arena_client: ArenaClient, exploration_client: ExplorationClient):
        self._client = arena_client
        self._expl_client = exploration_client

    def _get_ui(self, state_data: dict) -> ArenaUIService:
        """Внутренняя фабрика для UI сервиса."""
        session_context = state_data.get(FSM_CONTEXT_KEY, {})
        char_id = session_context.get("char_id")

        # Если char_id нет в контексте, пробуем найти в корне
        if not char_id:
            char_id = state_data.get("char_id")

        return ArenaUIService(state_data=state_data, char_id=char_id)

    # --- Обертки для доступа к координатам сообщений через UI ---
    def get_content_coords(self, state_data: dict) -> MessageCoordsDTO | None:
        """Возвращает (chat_id, message_id) для основного контента."""
        data = self._get_ui(state_data).get_message_content_data()
        return MessageCoordsDTO(chat_id=data[0], message_id=data[1]) if data else None

    def get_menu_coords(self, state_data: dict) -> MessageCoordsDTO | None:
        """Возвращает (chat_id, message_id) для меню."""
        data = self._get_ui(state_data).get_message_menu_data()
        return MessageCoordsDTO(chat_id=data[0], message_id=data[1]) if data else None

    # -----------------------------------------------------------

    async def handle_toggle_queue(self, mode: str, char_id: int, state_data: dict) -> ArenaViewDTO:
        """
        Обрабатывает запрос на вход/выход из очереди и возвращает готовый UI.
        """
        ui = self._get_ui(state_data)
        response = await self._client.toggle_queue(mode, char_id)

        if response.status == "joined":
            view = await ui.view_searching_screen(match_type=mode, gs=response.gs)
            return ArenaViewDTO(content=view)
        elif response.status == "cancelled":
            view = await ui.view_mode_menu(match_type=mode)
            return ArenaViewDTO(content=view)
        else:
            raise ArenaBotOrchestratorError(f"Queue toggle failed: {response.message}")

    async def handle_check_match(self, mode: str, char_id: int, state_data: dict) -> ArenaViewDTO | None:
        """
        Проверяет статус матча. Возвращает UI, если матч найден, иначе None.
        """
        ui = self._get_ui(state_data)
        response = await self._client.check_match(mode, char_id)

        if response.status in ("found", "created_shadow"):
            view = await ui.view_match_found(session_id=response.session_id, metadata=response.metadata)
            return ArenaViewDTO(content=view, session_id=response.session_id)

        if response.status == "error":
            raise ArenaBotOrchestratorError("Match check failed on backend")

        return None

    async def get_mode_menu(self, mode: str, state_data: dict) -> ArenaViewDTO:
        """Возвращает меню режима."""
        ui = self._get_ui(state_data)
        view = await ui.view_mode_menu(mode)
        return ArenaViewDTO(content=view)

    async def get_main_menu(self, state_data: dict) -> ArenaViewDTO:
        """Возвращает главное меню арены."""
        ui = self._get_ui(state_data)
        view = await ui.view_main_menu()
        return ArenaViewDTO(content=view)

    async def leave_arena(self, char_id: int, state_data: dict) -> ArenaViewDTO:
        """Выход с арены в мир."""
        # Получаем текущую локацию через клиент
        loc_dto = await self._expl_client.get_current_location(char_id)

        if loc_dto:
            from apps.bot.ui_service.exploration.exploration_ui import ExplorationUIService

            expl_ui = ExplorationUIService(state_data=state_data, char_id=char_id)
            view = expl_ui.render_navigation(loc_dto)
            return ArenaViewDTO(content=view, new_state="InGame:navigation")

        return ArenaViewDTO(content=ViewResultDTO(text="Ошибка загрузки локации."), new_state="InGame:navigation")
