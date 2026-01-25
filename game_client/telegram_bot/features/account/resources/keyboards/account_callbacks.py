from aiogram.filters.callback_data import CallbackData


class LobbyEntryCallback(CallbackData, prefix="acc_entry"):
    action: str  # "adventure"


class LobbyCallback(CallbackData, prefix="acc_lobby"):
    action: str  # "select", "login", "create", "delete", "delete_confirm", "delete_cancel"
    char_id: int | None = None


class OnboardingCallback(CallbackData, prefix="acc_onboard"):
    action: str  # "set_gender", "finalize"
    value: str | None = None
