from pydantic import BaseModel

from game_client.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


class InventoryViewDTO(BaseModel):
    """
    DTO для ответов оркестратора Инвентаря.
    """

    content: ViewResultDTO | None = None
    menu: ViewResultDTO | None = None

    # Метаданные для навигации
    current_page: int = 0
    total_pages: int = 0
    section: str | None = None
    category: str | None = None
    item_id: int | None = None
