# apps/bot/ui_service/exploration/exploration_ui.py

from aiogram.types import InlineKeyboardMarkup
from loguru import logger as log

from apps.bot.core_client.exploration import ExplorationClient
from apps.bot.ui_service.exploration.encounter_ui import EncounterUI
from apps.bot.ui_service.exploration.navigation_ui import NavigationUI
from apps.common.schemas_dto.exploration_dto import EncounterDTO, EncounterType, WorldNavigationDTO


class ExplorationUIService:
    """
    UI-Оркестратор для процесса исследования мира.
    Единая точка входа для любых действий с картой (перемещение, отрисовка, события).
    """

    def __init__(
        self,
        exploration_client: ExplorationClient,
    ):
        self._client = exploration_client
        self._encounter_ui = EncounterUI
        log.debug("ExplorationUIService | status=initialized")

    async def move_character(
        self, char_id: int, target_loc_id: str, actor_name: str = "Игрок"
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        """
        Обрабатывает намерение игрока переместиться.
        """
        result = await self._client.move(char_id, target_loc_id)

        if isinstance(result, EncounterDTO):
            log.info(f"ExplorationUI | Encounter received for char_id={char_id}")
            if result.type == EncounterType.COMBAT:
                return self._encounter_ui.render_combat_preview(result)
            else:
                return self._encounter_ui.render_narrative(result)

        if isinstance(result, WorldNavigationDTO):
            log.info(f"ExplorationUI | Move success for char_id={char_id}. Rendering map.")
            nav_ui = NavigationUI(char_id=char_id, actor_name=actor_name)
            return nav_ui.render_location(result)

        log.warning(f"ExplorationUI | Move confirm returned None for char_id={char_id}")
        return ("🚫 <b>Путь заблокирован</b> или локация недоступна.", None)

    async def render_map(self, char_id: int, actor_name: str = "Симбиот") -> tuple[str, InlineKeyboardMarkup | None]:
        """
        Просто отрисовывает карту текущей локации (без перемещения).
        Используется при входе в игру, возврате из меню/боя.
        """
        dto = await self._client.get_current_location(char_id)

        if not dto:
            log.error(f"ExplorationUI | Failed to get location data for char_id={char_id}")
            return ("Ошибка загрузки локации.", None)

        nav_ui = NavigationUI(char_id=char_id, actor_name=actor_name)
        return nav_ui.render_location(dto)
