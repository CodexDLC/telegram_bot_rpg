from aiogram.types import InlineKeyboardMarkup

from apps.bot.core_client.arena_client import ArenaClient
from apps.bot.ui_service.arena_ui_service.arena_ui_service import ArenaUIService


class ArenaBotOrchestratorError(Exception):
    """Ошибка в работе оркестратора арены."""

    pass


class ArenaBotOrchestrator:
    """
    Оркестратор на стороне бота.
    Связывает вызовы к "бэкенду" (через ArenaClient) с отрисовкой UI (через ArenaUIService).
    Предоставляет хендлерам готовые для отправки пользователю данные.
    """

    def __init__(self, arena_client: ArenaClient, char_id: int, actor_name: str):
        self._client = arena_client
        self._ui = ArenaUIService(char_id=char_id, actor_name=actor_name)

    async def handle_toggle_queue(self, mode: str, char_id: int) -> tuple[str, InlineKeyboardMarkup]:
        """
        Обрабатывает запрос на вход/выход из очереди и возвращает готовый UI.
        Raises:
            ArenaBotOrchestratorError: Если бэкенд вернул ошибку.
        """
        response = await self._client.toggle_queue(mode, char_id)

        if response.status == "joined":
            return await self._ui.view_searching_screen(match_type=mode, gs=response.gs)
        elif response.status == "cancelled":
            # После отмены показываем меню режима, из которого вышли
            return await self._ui.view_mode_menu(match_type=mode)
        else:
            # Если статус error или неизвестный, выбрасываем исключение,
            # чтобы хендлер обработал его через UIErrorHandler
            raise ArenaBotOrchestratorError(f"Queue toggle failed: {response.message}")

    async def handle_check_match(self, mode: str, char_id: int) -> tuple[str, InlineKeyboardMarkup] | None:
        """
        Проверяет статус матча. Возвращает UI, если матч найден, иначе None.
        """
        response = await self._client.check_match(mode, char_id)

        if response.status in ("found", "created_shadow"):
            # Если матч найден, рендерим экран с кнопкой "В БОЙ"
            return await self._ui.view_match_found(session_id=response.session_id, metadata=response.metadata)

        if response.status == "error":
            raise ArenaBotOrchestratorError("Match check failed on backend")

        # Если статус 'waiting', возвращаем None.
        # Хендлер должен будет продолжить опрос.
        return None
