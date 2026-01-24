from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder


class StartMenuCallback(CallbackData, prefix="start"):
    action: str  # "adventure", "settings", "help"


def get_error_keyboard() -> InlineKeyboardBuilder:
    """
    Клавиатура для экрана ошибки (возврат в главное меню).
    """
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="🔄 В главное меню", callback_data=StartMenuCallback(action="adventure").pack())
    kb_builder.adjust(1)
    return kb_builder
