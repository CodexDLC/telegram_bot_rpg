# game_client/telegram_bot/features/exploration/system/interaction_orchestrator.py

from collections.abc import Awaitable, Callable
from typing import Any

from common.schemas.enums import CoreDomain
from common.schemas.exploration import DetectionStatus, EncounterDTO, ExplorationListDTO, WorldNavigationDTO
from common.schemas.response import CoreResponseDTO
from game_client.telegram_bot.base.base_orchestrator import BaseBotOrchestrator
from game_client.telegram_bot.base.view_dto import UnifiedViewDTO, ViewResultDTO
from game_client.telegram_bot.features.exploration.client import ExplorationClient
from game_client.telegram_bot.features.exploration.system.components import EncounterUI, ListUI, NavigationUI


class InteractionOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор взаимодействий: поиск, сканирование, encounter, списки.
    Вызывается из NavigationOrchestrator или напрямую через Director.
    """

    def __init__(self, client: ExplorationClient):
        super().__init__(expected_state=CoreDomain.EXPLORATION)
        self._client = client

    async def render(self, payload: Any) -> UnifiedViewDTO:
        """
        Entry point от Director.
        Рендерит interaction payload (encounter, list, etc).
        """
        char_id = await self.director.get_char_id()
        if not char_id:
            return UnifiedViewDTO(content=ViewResultDTO(text="Ошибка: Персонаж не выбран."))

        if payload:
            return self._process_response_dto(payload, char_id)

        # Если нет payload — возвращаемся в навигацию
        return await self._redirect_to_navigation(None)

    # =========================================================================
    # Handlers (Direct)
    # =========================================================================

    async def handle_interact(self, char_id: int, action: str, target_id: str | None = None) -> UnifiedViewDTO:
        """Обрабатывает взаимодействие (поиск, скан, атака, осмотр)."""
        response = await self._client.interact(char_id, action, target_id)

        redirect = await self.check_and_switch_state(response)
        if redirect:
            return redirect

        return self._process_response(response, char_id)

    async def handle_list_action(
        self, char_id: int, action: str, item_id: str | None = None, page: int = 1
    ) -> UnifiedViewDTO:
        """Обрабатывает действия со списком (пагинация, выбор)."""
        if action == "page":
            # TODO: Backend pagination support
            response = await self._client.interact(char_id, "scan_battles", None)
        elif action == "select" and item_id:
            # Парсинг item_id: "battle:123" -> action="spectate", target="123"
            item_type, target = self._parse_item_id(item_id)
            interact_action = self._map_item_type_to_action(item_type)
            response = await self._client.interact(char_id, interact_action, target)
        else:
            return UnifiedViewDTO(content=ViewResultDTO(text="Неизвестное действие списка."))

        redirect = await self.check_and_switch_state(response)
        if redirect:
            return redirect

        return self._process_response(response, char_id)

    # =========================================================================
    # Fetch Logic (for run_delayed_fetch)
    # =========================================================================

    def get_search_fetcher(
        self, char_id: int, action: str, target_id: str | None
    ) -> Callable[[], Awaitable[tuple[UnifiedViewDTO, bool]]]:
        """
        Возвращает функцию для отложенного запроса (search, scan).
        Вызывается один раз после анимации.
        """

        async def fetcher() -> tuple[UnifiedViewDTO, bool]:
            try:
                response = await self._client.interact(char_id, action, target_id)

                redirect = await self.check_and_switch_state(response)
                if redirect:
                    return redirect, False

                view = self._process_response(response, char_id)
                return view, False

            except Exception as e:  # noqa: BLE001
                error_view = UnifiedViewDTO(content=ViewResultDTO(text=f"🚫 Ошибка: {e}"), alert_text="Ошибка сети")
                return error_view, False

        return fetcher

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
            if payload_type == "encounter" or "enemies" in data or "options" in data:
                data = EncounterDTO(**data)
            elif payload_type == "list" or "items" in data:
                data = ExplorationListDTO(**data)
            elif payload_type == "navigation" or "grid" in data:
                data = WorldNavigationDTO(**data)
            elif "text" in data and "kb" in data:
                data = ViewResultDTO(**data)

        # Рендеринг
        if isinstance(data, ViewResultDTO):
            return UnifiedViewDTO(content=data)

        if isinstance(data, EncounterDTO):
            view = EncounterUI().render(data)
            alert = "⚔️ ЗАСАДА!" if data.status == DetectionStatus.AMBUSH else None
            return UnifiedViewDTO(content=view, alert_text=alert)

        if isinstance(data, ExplorationListDTO):
            view = ListUI().render(data)
            return UnifiedViewDTO(content=view)

        # Navigation — должен обрабатываться NavigationOrchestrator
        if isinstance(data, WorldNavigationDTO):
            view = NavigationUI().render(data)
            return UnifiedViewDTO(content=view)

        return UnifiedViewDTO(alert_text="Неизвестный тип данных.")

    # =========================================================================
    # Internal Routing
    # =========================================================================

    async def _redirect_to_navigation(self, payload: Any) -> UnifiedViewDTO:
        """Перенаправляет в NavigationOrchestrator."""
        return await self.director.render(CoreDomain.EXPLORATION, "navigation", payload)

    def _parse_item_id(self, item_id: str) -> tuple[str, str]:
        """Парсит item_id формата 'type:id' -> (type, id)"""
        if ":" in item_id:
            parts = item_id.split(":", 1)
            return parts[0], parts[1]
        return "unknown", item_id

    def _map_item_type_to_action(self, item_type: str) -> str:
        """Маппинг типа элемента на action для interact."""
        mapping = {
            "battle": "spectate",
            "char": "inspect",
            "npc": "talk",
        }
        return mapping.get(item_type, "inspect")
