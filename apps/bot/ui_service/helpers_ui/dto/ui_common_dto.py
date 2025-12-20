from aiogram.types import InlineKeyboardMarkup
from pydantic import BaseModel, ConfigDict


class MessageCoordsDTO(BaseModel):
    """
    DTO для координат сообщения (chat_id, message_id).
    Используется для безопасного доступа к ID без индексов.
    """

    chat_id: int
    message_id: int


class ViewResultDTO(BaseModel):
    """
    DTO для представления одного сообщения (текст + клавиатура).
    """

    text: str
    kb: InlineKeyboardMarkup | None = None

    # Разрешаем произвольные типы (для InlineKeyboardMarkup)
    model_config = ConfigDict(arbitrary_types_allowed=True)
