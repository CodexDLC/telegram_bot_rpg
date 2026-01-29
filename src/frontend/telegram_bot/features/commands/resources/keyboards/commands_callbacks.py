from aiogram.filters.callback_data import CallbackData


class SystemCallback(CallbackData, prefix="sys"):
    """
    Глобальный callback для системных действий (logout, main_menu).
    """

    action: str  # "logout", "main_menu"


class SettingsCallback(CallbackData, prefix="cmd_settings"):
    action: str  # "open", "toggle_notifications", "change_language", etc.
