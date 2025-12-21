# apps/bot/ui_service/exploration/exploration_ui.py

from typing import Any

from loguru import logger as log

from apps.bot.ui_service.base_service import BaseUIService
from apps.bot.ui_service.exploration.encounter_ui import EncounterUI
from apps.bot.ui_service.exploration.navigation_ui import NavigationUI
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO
from apps.common.schemas_dto.exploration_dto import EncounterDTO, EncounterType, WorldNavigationDTO


class ExplorationUIService(BaseUIService):
    """
    Чистый UI-сервис для Исследования.
    Отвечает только за рендеринг интерфейсов (карта, превью встречи).
    """

    def __init__(self, state_data: dict[str, Any], char_id: int | None = None):
        super().__init__(state_data, char_id)
        self._encounter_ui = EncounterUI
        log.debug(f"ExplorationUIService | Initialized for char_id={self.char_id}")

    def render_navigation(self, dto: WorldNavigationDTO) -> ViewResultDTO:
        """Рендерит карту локации."""
        nav_ui = NavigationUI(char_id=self.char_id, actor_name=self.actor_name)
        return nav_ui.render_location(dto)

    def render_encounter(self, dto: EncounterDTO) -> ViewResultDTO:
        """Рендерит превью встречи (бой или событие)."""
        if dto.type == EncounterType.COMBAT:
            return self._encounter_ui.render_combat_preview(dto)
        else:
            return self._encounter_ui.render_narrative(dto)
