from pydantic import BaseModel

from src.frontend.telegram_bot.base.view_dto import ViewResultDTO


class StatusViewDTO(BaseModel):
    """DTO для ответов оркестратора Статуса."""

    content: ViewResultDTO | None = None
    char_id: int | None = None
    current_tab: str | None = None
