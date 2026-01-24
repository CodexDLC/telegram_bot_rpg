from pydantic import BaseModel

from game_client.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


class ArenaViewDTO(BaseModel):
    """
    DTO для ответов оркестратора Арены.
    """

    content: ViewResultDTO | None = None
    menu: ViewResultDTO | None = None
    fsm_update: dict | None = None
    new_state: str | None = None

    # Специфичные поля для арены (если понадобятся)
    session_id: str | None = None
