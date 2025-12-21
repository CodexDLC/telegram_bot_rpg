from pydantic import BaseModel

from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


class CombatViewDTO(BaseModel):
    """
    DTO для полного ответа оркестратора.
    Содержит данные для обновления дашборда, лога и ID цели.
    """

    session_id: str | None = None  # ID сессии (для старта боя)
    target_id: int | None = None
    content: ViewResultDTO | None = None
    menu: ViewResultDTO | None = None
    new_state: str | None = None  # Куда переключить FSM (для выхода из боя)
    alert_text: str | None = None  # Текст для всплывающего уведомления (call.answer)

    # Данные для обновления FSM (например, новый selection или выбранная способность)
    fsm_update: dict | None = None
