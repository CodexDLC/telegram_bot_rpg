from dataclasses import dataclass

from aiogram.types import InlineKeyboardMarkup


@dataclass
class MenuViewDTO:
    """
    Универсальный DTO для передачи готового UI (текст + клавиатура)
    от сервисного слоя к хендлерам.
    """

    text: str
    keyboard: InlineKeyboardMarkup | None = None
