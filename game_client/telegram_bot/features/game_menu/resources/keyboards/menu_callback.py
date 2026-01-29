from aiogram.filters.callback_data import CallbackData


class MenuCallback(CallbackData, prefix="menu"):
    """
    Callback data для кнопок главного меню.
    """

    action: str
