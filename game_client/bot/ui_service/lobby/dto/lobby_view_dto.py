from pydantic import BaseModel

from game_client.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


class LobbyViewDTO(BaseModel):
    """
    DTO для ответов оркестратора Лобби.
    """

    content: ViewResultDTO | None = None
    new_char_id: int | None = None
    is_deleted: bool = False
