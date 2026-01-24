from dataclasses import dataclass

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


@dataclass
class UnifiedViewDTO:
    """
    Единый DTO ответа от Оркестратора.
    Содержит данные для двух сообщений (Content и Menu) и флаги управления.
    """

    content: ViewResultDTO | None = None
    menu: ViewResultDTO | None = None
    clean_history: bool = False
    alert_text: str | None = None  # Для всплывающих уведомлений (answer_callback_query)


@dataclass
class MenuViewDTO:
    """
    Универсальный DTO для передачи готового UI (текст + клавиатура)
    от сервисного слоя к хендлерам.
    """

    text: str
    keyboard: InlineKeyboardMarkup | None = None
