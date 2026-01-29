from collections.abc import Awaitable, Callable
from typing import Any

from src.frontend.telegram_bot.base.base_orchestrator import BaseBotOrchestrator
from src.frontend.telegram_bot.base.view_dto import UnifiedViewDTO
from src.frontend.telegram_bot.features.arena.client import ArenaClient
from src.frontend.telegram_bot.features.arena.resources.keyboards.arena_callback import ArenaCallback
from src.frontend.telegram_bot.features.arena.system.arena_ui_service import ArenaUIService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.arena import ArenaActionEnum, ArenaScreenEnum
from src.shared.schemas.response import CoreResponseDTO


class ArenaBotOrchestrator(BaseBotOrchestrator):
    def __init__(self, client: ArenaClient, ui_service: ArenaUIService):
        super().__init__(expected_state=CoreDomain.ARENA)
        self.client = client
        self.ui_service = ui_service

    async def render(self, payload: Any) -> UnifiedViewDTO:
        """
        Реализация абстрактного метода render.
        Превращает payload в UnifiedViewDTO.
        """
        view_result = self.ui_service.render_screen(payload)
        return UnifiedViewDTO(content=view_result)

    async def handle_request(self, user_id: int, callback_data: ArenaCallback) -> UnifiedViewDTO | None:
        """
        Обрабатывает callback от пользователя (кроме join_queue, который обрабатывается отдельно).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            # TODO: Обработка ошибки, если char_id не найден
            return None

        # 1. Отправляем запрос на backend
        response: CoreResponseDTO = await self.client.action(
            char_id=char_id, action=callback_data.action, mode=callback_data.mode, value=callback_data.value
        )

        # 2. Проверяем смену состояния (redirect)
        redirect_result = await self.check_and_switch_state(response)
        if redirect_result:
            return redirect_result

        # 3. Если остались в ARENA, рендерим UI
        if response.payload:
            return await self.render(response.payload)

        return None

    # --- Polling Logic ---

    def get_search_poller(
        self, user_id: int, callback: ArenaCallback
    ) -> Callable[[], Awaitable[tuple[UnifiedViewDTO, bool]]]:
        """
        Возвращает функцию для поллинга.
        """
        is_first_run = True

        async def poller() -> tuple[UnifiedViewDTO, bool]:
            nonlocal is_first_run
            if is_first_run:
                is_first_run = False
                return await self._handle_join_queue(callback)
            else:
                # Проверяем, что mode не None перед передачей
                if callback.mode is None:
                    # Если mode не задан, используем дефолтный или прерываем
                    # В данном контексте лучше вернуть пустой view и остановить поллинг
                    return UnifiedViewDTO(), False
                return await self._check_match_status(callback.mode)

        return poller

    async def _handle_join_queue(self, callback: ArenaCallback) -> tuple[UnifiedViewDTO, bool]:
        """
        Первый шаг поллинга: отправка запроса на вступление в очередь.
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return UnifiedViewDTO(), False  # Error

        response: CoreResponseDTO = await self.client.action(
            char_id=char_id, action=ArenaActionEnum.JOIN_QUEUE.value, mode=callback.mode
        )

        # Проверяем смену состояния (вдруг сразу нашли матч?)
        redirect_result = await self.check_and_switch_state(response)
        if redirect_result:
            return redirect_result, False  # Stop polling

        if response.payload:
            view = await self.render(response.payload)
            # Если экран SEARCHING, то продолжаем поллинг
            is_waiting = response.payload.get("screen") == ArenaScreenEnum.SEARCHING.value
            return view, is_waiting

        return UnifiedViewDTO(), False

    async def _check_match_status(self, mode: str) -> tuple[UnifiedViewDTO, bool]:
        """
        Последующие шаги поллинга: проверка статуса.
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return UnifiedViewDTO(), False

        response: CoreResponseDTO = await self.client.action(
            char_id=char_id, action=ArenaActionEnum.CHECK_MATCH.value, mode=mode
        )

        # Проверяем смену состояния (COMBAT)
        redirect_result = await self.check_and_switch_state(response)
        if redirect_result:
            return redirect_result, False  # Stop polling (Match found!)

        if response.payload:
            view = await self.render(response.payload)
            is_waiting = response.payload.get("screen") == ArenaScreenEnum.SEARCHING.value
            return view, is_waiting

        return UnifiedViewDTO(), False
