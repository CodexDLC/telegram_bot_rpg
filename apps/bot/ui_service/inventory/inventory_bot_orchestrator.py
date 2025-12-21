from apps.bot.core_client.inventory_client import InventoryClient
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import MessageCoordsDTO, ViewResultDTO
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.inventory.dto.inventory_view_dto import InventoryViewDTO
from apps.bot.ui_service.inventory.inventory_ui_service import InventoryUIService


class InventoryBotOrchestrator:
    """
    Оркестратор инвентаря на стороне бота.
    """

    def __init__(self, inventory_client: InventoryClient):
        self._client = inventory_client

    def _get_ui(self, state_data: dict, user_id: int) -> InventoryUIService:
        """Внутренняя фабрика для UI сервиса."""
        session_context = state_data.get(FSM_CONTEXT_KEY, {})
        char_id = session_context.get("char_id")

        if not char_id:
            char_id = state_data.get("char_id")

        return InventoryUIService(char_id=char_id, user_id=user_id, state_data=state_data)

    # --- Обертки для доступа к координатам сообщений через UI ---
    def get_content_coords(self, state_data: dict, user_id: int) -> MessageCoordsDTO | None:
        """Возвращает (chat_id, message_id) для основного контента."""
        data = self._get_ui(state_data, user_id).get_message_content_data()
        return MessageCoordsDTO(chat_id=data[0], message_id=data[1]) if data else None

    # -----------------------------------------------------------

    async def get_main_menu(self, char_id: int, user_id: int, state_data: dict) -> InventoryViewDTO:
        """Возвращает главное меню инвентаря."""
        ui = self._get_ui(state_data, user_id)

        # Получаем данные из Core
        summary = await self._client.get_summary(char_id)

        # Получаем экипировку
        equipped_data = await self._client.get_items(char_id, "equipped", "all", 0, 100)
        equipped = equipped_data.get("items", [])

        view = ui.render_main_menu(summary, equipped)
        return InventoryViewDTO(content=view)

    async def get_item_list(
        self,
        char_id: int,
        user_id: int,
        section: str,
        category: str,
        page: int,
        state_data: dict,
        filter_type: str = "category",
    ) -> InventoryViewDTO:
        """Возвращает список предметов."""
        ui = self._get_ui(state_data, user_id)

        # Получаем данные из Core
        page_size = 9
        data = await self._client.get_items(char_id, section, category, page, page_size)

        items = data.get("items", [])
        total_pages = data.get("total_pages", 1)
        current_page = data.get("current_page", 0)

        view = ui.render_item_list(items, total_pages, current_page, section, category, filter_type)
        return InventoryViewDTO(content=view, current_page=current_page, total_pages=total_pages)

    async def get_item_details(
        self, char_id: int, user_id: int, item_id: int, category: str, page: int, filter_type: str, state_data: dict
    ) -> InventoryViewDTO:
        """Возвращает детали предмета."""
        ui = self._get_ui(state_data, user_id)

        item = await self._client.get_item_details(char_id, item_id)
        if not item:
            return InventoryViewDTO(content=ViewResultDTO(text="Предмет не найден."))

        # Получаем данные для сравнения
        comparison = await self._client.get_comparison(char_id, item)

        view = ui.render_item_details(item, comparison, category, page, filter_type)
        return InventoryViewDTO(content=view, item_id=item_id)

    async def handle_equip_action(
        self, char_id: int, user_id: int, item_id: int, action: str, state_data: dict
    ) -> InventoryViewDTO:
        """Обрабатывает экипировку/снятие."""
        # Логика экипировки
        if action == "equip":
            # success, msg = await self._client.equip_item(char_id, item_id, "auto") # auto slot # Удалено: не используется
            await self._client.equip_item(char_id, item_id, "auto")
        elif action == "unequip":
            # unequip тоже через equip_item? Или отдельный метод?
            # В InventoryService unequip обычно это equip(None) или unequip.
            # В InventoryCoreOrchestrator equip_item - заглушка.
            # success, msg = True, "Unequipped" # Удалено: не используется
            pass
        else:
            # success, msg = False, "Unknown action" # Удалено: не используется
            pass

        # Возвращаем DTO с сообщением (alert) и обновленным видом (если нужно).
        # Пока просто вернем главное меню.
        return await self.get_main_menu(char_id, user_id, state_data)

    async def get_belt_overview(self, char_id: int, user_id: int, state_data: dict) -> InventoryViewDTO:
        """Возвращает обзор пояса."""
        ui = self._get_ui(state_data, user_id)

        max_slots = await self._client.get_quick_slot_limit(char_id)

        # Получаем все предметы (чтобы найти те, что в слотах)
        items_data = await self._client.get_items(char_id, "inventory", "all", 0, 1000)
        items = items_data.get("items", [])

        view = ui.render_belt_overview(max_slots, items)
        return InventoryViewDTO(content=view)

    async def get_quick_slot_selection_menu(
        self, char_id: int, user_id: int, item_id: int, context_data: dict, state_data: dict
    ) -> InventoryViewDTO:
        """Возвращает меню выбора слота."""
        ui = self._get_ui(state_data, user_id)

        item = await self._client.get_item_details(char_id, item_id)
        if not item:
            return InventoryViewDTO(content=ViewResultDTO(text="Предмет не найден."))

        max_slots = await self._client.get_quick_slot_limit(char_id)

        view = ui.render_quick_slot_selection_menu(item.data.name, item_id, max_slots, context_data)
        return InventoryViewDTO(content=view)

    async def handle_quick_slot_action(
        self, char_id: int, user_id: int, item_id: int, action: str, slot_key: str | None, state_data: dict
    ) -> InventoryViewDTO:
        """Обрабатывает действия с быстрыми слотами."""
        if action == "bind":
            if slot_key:
                # success, msg = await self._client.bind_quick_slot(char_id, item_id, slot_key) # Удалено: не используется
                await self._client.bind_quick_slot(char_id, item_id, slot_key)
            else:
                # success, msg = False, "Slot key missing" # Удалено: не используется
                pass
        elif action == "unbind":
            # success, msg = await self._client.unbind_quick_slot(char_id, item_id) # Удалено: не используется
            await self._client.unbind_quick_slot(char_id, item_id)
        else:
            # success, msg = False, "Unknown action" # Удалено: не используется
            pass

        return InventoryViewDTO(content=None)  # Хендлер сам обновит UI
