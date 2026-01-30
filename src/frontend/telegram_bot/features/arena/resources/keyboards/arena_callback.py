from aiogram.filters.callback_data import CallbackData


class ArenaCallback(CallbackData, prefix="arena"):
    action: str
    mode: str | None = None
    value: str | None = None
