from dataclasses import dataclass

from aiogram.types import InlineKeyboardMarkup

from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


@dataclass
class MenuViewDTO:
    """
    Универсальный DTO для передачи готового UI (текст + клавиатура)
    от сервисного слоя к хендлерам.
    """

    text: str
    keyboard: InlineKeyboardMarkup | None = None


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
