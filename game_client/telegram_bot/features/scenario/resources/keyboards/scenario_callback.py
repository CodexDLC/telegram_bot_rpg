from aiogram.filters.callback_data import CallbackData


class ScenarioCallback(CallbackData, prefix="sc"):
    """
    Универсальный колбэк для системы сценариев.
    """

    action: str  # "initialize", "step"
    quest_key: str | None = None  # Для инициализации
    action_id: str | None = None  # Для шага
