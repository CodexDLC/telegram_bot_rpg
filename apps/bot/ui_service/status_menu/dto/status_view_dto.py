from pydantic import BaseModel

from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


class StatusViewDTO(BaseModel):
    """DTO для ответов оркестратора Статуса."""

    content: ViewResultDTO | None = None
    char_id: int | None = None
    current_tab: str | None = None
