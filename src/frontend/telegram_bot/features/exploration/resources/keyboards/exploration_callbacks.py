# frontend/telegram_bot/features/exploration/resources/keyboards/exploration_callbacks.py


from aiogram.filters.callback_data import CallbackData


class NavigationCallback(CallbackData, prefix="exp_nav"):
    """
    Колбэк для перемещения.
    """

    action: str = "move"
    target_id: str | None = None  # ID целевой локации
    duration: float = 0.0  # Время перехода


class EncounterCallback(CallbackData, prefix="exp_enc"):
    """
    Колбэк для взаимодействия и событий.
    """

    action: str  # search, attack, inspect, scan_battles, scan_people
    target_id: str | None = None


class ExplorationListCallback(CallbackData, prefix="exp_list"):
    """
    Колбэк для списков (пагинация, выбор).
    """

    action: str  # page, select
    page: int | None = None
    item_id: str | None = None
