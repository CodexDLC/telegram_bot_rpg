from aiogram.types import InlineKeyboardMarkup
from pydantic import BaseModel, ConfigDict


class ViewResultDTO(BaseModel):
    """
    DTO для представления одного сообщения (текст + клавиатура).
    """

    text: str
    kb: InlineKeyboardMarkup | None = None

    # Разрешаем произвольные типы (для InlineKeyboardMarkup)
    model_config = ConfigDict(arbitrary_types_allowed=True)


class MessageCoordsDTO(BaseModel):
    """
    Координаты сообщения в Telegram.
    """

    chat_id: int
    message_id: int


class UnifiedViewDTO(BaseModel):
    """
    Единый DTO ответа от Оркестратора.
    Содержит данные для двух сообщений (Content и Menu) и флаги управления.
    """

    content: ViewResultDTO | None = None
    menu: ViewResultDTO | None = None
    clean_history: bool = False
    alert_text: str | None = None  # Для всплывающих уведомлений (answer_callback_query)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MenuViewDTO(BaseModel):
    """
    Универсальный DTO для передачи готового UI (текст + клавиатура)
    от сервисного слоя к хендлерам.
    """

    text: str
    keyboard: InlineKeyboardMarkup | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
