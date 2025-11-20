from pydantic import BaseModel


class SessionDataDTO(BaseModel):
    """
    ДТО для хранения основного контекста сессии (Ядра FSM).
    """

    user_id: int | None = None
    char_id: int | None = None
    message_menu: dict[str, int] | None = None
    message_content: dict[str, int] | None = None
