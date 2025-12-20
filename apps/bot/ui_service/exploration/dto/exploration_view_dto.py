from pydantic import BaseModel

from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


class ExplorationViewDTO(BaseModel):
    """
    DTO для ответов оркестратора Навигации.
    """

    content: ViewResultDTO | None = None
    menu: ViewResultDTO | None = None
    new_state: str | None = None
    fsm_update: dict | None = None

    # Текст для всплывающего уведомления (call.answer)
    alert_text: str | None = None

    # Метаданные встречи (если есть)
    encounter_id: str | None = None

    # Если переходим в бой, можем вернуть session_id
    combat_session_id: str | None = None
    combat_target_id: int | None = None
