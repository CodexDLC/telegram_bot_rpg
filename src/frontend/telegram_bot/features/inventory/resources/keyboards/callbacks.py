from aiogram.filters.callback_data import CallbackData

from src.shared.enums.inventory_enums import InventoryActionType, InventoryViewTarget


class InventoryViewCB(CallbackData, prefix="inv_v"):
    """
    Колбэк для навигации (GET).
    """

    target: InventoryViewTarget
    # Payload передаем как строку (JSON) или отдельные поля, если влезают
    # Aiogram имеет лимит 64 байта.
    # Поэтому лучше использовать короткие алиасы или ID.
    section: str | None = None
    category: str | None = None
    page: int = 0
    item_id: int | None = None


class InventoryActionCB(CallbackData, prefix="inv_a"):
    """
    Колбэк для действий (POST/DELETE).
    """

    action: InventoryActionType
    item_id: int
    slot: str | None = None
