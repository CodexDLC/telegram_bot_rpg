from game_client.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


class AuthViewDTO:
    """DTO для ответа оркестратора авторизации."""

    content: ViewResultDTO | None = None
    menu: ViewResultDTO | None = None
    new_state: str | None = None
    fsm_update: dict | None = None
    game_stage: str | None = None
