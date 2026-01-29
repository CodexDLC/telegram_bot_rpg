# frontend/telegram_bot/features/exploration/system/navigation_orchestrator.py

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.fsm.context import FSMContext
from pydantic import ValidationError

from src.frontend.telegram_bot.base.base_orchestrator import BaseBotOrchestrator
from src.frontend.telegram_bot.base.view_dto import UnifiedViewDTO, ViewResultDTO
from src.frontend.telegram_bot.features.exploration.client import ExplorationClient
from src.frontend.telegram_bot.features.exploration.system.components import EncounterUI, NavigationUI
from src.frontend.telegram_bot.features.exploration.system.exploration_state_manager import ExplorationStateManager
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.exploration import DetectionStatus, EncounterDTO, WorldNavigationDTO
from src.shared.schemas.response import CoreResponseDTO


class NavigationOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор навигации: перемещение, обзор локации, grid.
    Entry point для Exploration feature.
    """

    def __init__(self, client: ExplorationClient):
        super().__init__(expected_state=CoreDomain.EXPLORATION)
        self._client = client

    async def render(self, payload: Any) -> UnifiedViewDTO:
        """
        Entry point от Director.
        Рендерит navigation payload или делает look_around.
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return UnifiedViewDTO(content=ViewResultDTO(text="Ошибка: Персонаж не выбран."))

        if payload:
            return self._process_response_dto(payload, char_id)

        return await self.handle_look_around(char_id)

    # =========================================================================
    # Handlers (Direct)
    # =========================================================================

    async def handle_look_around(self, char_id: int) -> UnifiedViewDTO:
        """Обзор локации (без перемещения)."""
        response = await self._client.look_around(char_id)

        redirect = await self.check_and_switch_state(response)
        if redirect:
            return redirect

        return self._process_response(response, char_id)

    async def handle_move(self, char_id: int, target_id: str) -> UnifiedViewDTO:
        """Перемещение (синхронно, без анимации)."""
        response = await self._client.move(char_id, target_id=target_id)

        redirect = await self.check_and_switch_state(response)
        if redirect:
            return redirect

        return self._process_response(response, char_id)

    # =========================================================================
    # Polling Logic (Animation)
    # =========================================================================

    def get_move_poller(
        self, char_id: int, target_id: str, duration: float, state: FSMContext
    ) -> Callable[[], Awaitable[tuple[UnifiedViewDTO, bool]]]:
        """Возвращает функцию для поллинга перемещения."""
        manager = ExplorationStateManager(state)
        is_started = False

        async def poller() -> tuple[UnifiedViewDTO, bool]:
            nonlocal is_started

            if not is_started:
                is_started = True
                await manager.start_move()
                asyncio.create_task(self._bg_move_request(char_id, target_id, manager))
                return UnifiedViewDTO(content=ViewResultDTO(text="🚶 <b>Перемещение...</b>")), True

            (
                result_data,
                elapsed,
                _,
            ) = await manager.get_move_status()  # duration берем из аргумента, но manager тоже возвращает

            if result_data is None:
                return UnifiedViewDTO(content=ViewResultDTO(text="🚶 <b>Перемещение...</b>")), True

            # Если это ошибка (ViewResultDTO)
            if isinstance(result_data, ViewResultDTO) or (
                isinstance(result_data, dict) and "text" in result_data and "kb" in result_data
            ):
                dto = ViewResultDTO(**result_data) if isinstance(result_data, dict) else result_data
                return UnifiedViewDTO(content=dto), False

            # Восстанавливаем CoreResponseDTO
            try:
                response = CoreResponseDTO(**result_data)
            except (ValidationError, TypeError):
                return self._process_response_dto(result_data, char_id), False

            if elapsed < duration:
                return UnifiedViewDTO(
                    content=ViewResultDTO(text=f"🚶 <b>Перемещение...</b> ({int(duration - elapsed)}с)")
                ), True

            redirect = await self.check_and_switch_state(response)
            if redirect:
                return redirect, False

            # Проверяем на encounter — передаём в InteractionOrchestrator
            if self._is_encounter_response(response):
                return await self._redirect_to_interaction(response.payload, char_id), False

            view = self._process_response(response, char_id)
            return view, False

        return poller

    async def _bg_move_request(self, char_id: int, target_id: str, manager: ExplorationStateManager):
        """Фоновая задача: move"""
        try:
            response = await self._client.move(char_id, target_id=target_id)
            # Сохраняем результат. Duration уже не важен для результата, он важен для анимации.
            await manager.set_move_result(response.model_dump(), 0)
        except Exception as e:  # noqa: BLE001
            await manager.set_move_result(ViewResultDTO(text=f"Сбой сети: {e}").model_dump(), 0)

    # =========================================================================
    # Response Processor
    # =========================================================================

    def _process_response(self, response: CoreResponseDTO, char_id: int) -> UnifiedViewDTO:
        """Обработка CoreResponseDTO"""
        if response.header.error:
            error_text = f"🚫 Ошибка: {response.header.error}"
            return UnifiedViewDTO(content=ViewResultDTO(text=error_text), alert_text=response.header.error)

        data = response.payload
        return self._process_response_dto(data, char_id, response.payload_type)

    def _process_response_dto(self, data: Any, char_id: int, payload_type: str = None) -> UnifiedViewDTO:
        """Обработка данных (DTO или Dict)"""
        # Авто-конвертация из dict в DTO
        if isinstance(data, dict):
            if payload_type == "navigation" or "grid" in data:
                data = WorldNavigationDTO(**data)
            elif payload_type == "encounter" or "enemies" in data or "options" in data:
                data = EncounterDTO(**data)
            elif "text" in data and "kb" in data:
                data = ViewResultDTO(**data)

        # Рендеринг
        if isinstance(data, ViewResultDTO):
            return UnifiedViewDTO(content=data)

        if isinstance(data, WorldNavigationDTO):
            view = NavigationUI().render(data)
            return UnifiedViewDTO(content=view)

        # Encounter — должен обрабатываться InteractionOrchestrator
        if isinstance(data, EncounterDTO):
            view = EncounterUI().render(data)
            alert = "⚔️ ЗАСАДА!" if data.status == DetectionStatus.AMBUSH else None
            return UnifiedViewDTO(content=view, alert_text=alert)

        return UnifiedViewDTO(alert_text="Неизвестный тип данных.")

    # =========================================================================
    # Internal Routing
    # =========================================================================

    def _is_encounter_response(self, response: CoreResponseDTO) -> bool:
        """Проверяет, является ли ответ encounter'ом."""
        if response.payload_type == "encounter":
            return True
        if isinstance(response.payload, dict):
            return "enemies" in response.payload or "options" in response.payload
        return isinstance(response.payload, EncounterDTO)

    async def _redirect_to_interaction(self, payload: Any, char_id: int) -> UnifiedViewDTO:
        """Перенаправляет обработку encounter в InteractionOrchestrator."""
        return await self.director.render(CoreDomain.EXPLORATION, "interaction", payload)
