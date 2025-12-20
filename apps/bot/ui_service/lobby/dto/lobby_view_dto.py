from apps.bot.ui_service.ui_common_dto import ViewResultDTO
from pydantic import BaseModel


class LobbyViewDTO(BaseModel):
    """
    DTO для ответов оркестратора Лобби.
    """

    content: ViewResultDTO | None = None
    new_char_id: int | None = None
    is_deleted: bool = False
