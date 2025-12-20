from typing import Any, Protocol

from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import MessageCoordsDTO


class IBotOrchestrator(Protocol):
    """Общий интерфейс для любого оркестратора в Хабе."""

    def get_content_coords(self, state_data: dict[str, Any], user_id: int | None = None) -> MessageCoordsDTO | None: ...
