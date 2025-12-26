from apps.bot.core_client.inventory_client import InventoryClient
from apps.bot.resources.keyboards.inventory_callback import InventoryCallback
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import MessageCoordsDTO, ViewResultDTO
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.inventory.dto.inventory_view_dto import InventoryViewDTO
from apps.bot.ui_service.inventory.inventory_ui_service import InventoryUIService
from apps.common.schemas_dto.inventory_dto import (
    InventoryBagResponseDTO,
    InventoryItemDetailsResponseDTO,
    InventoryMainMenuResponseDTO,
)


class InventoryBotOrchestrator:
    """
    Оркестратор инвентаря на стороне бота.
    Связывает UI-слой (View) с Core-слоем (Logic) через Клиент.
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

    def get_content_coords(self, state_data: dict, user_id: int) -> MessageCoordsDTO | None:
        data = self._get_ui(state_data, user_id).get_message_content_data()
        return MessageCoordsDTO(chat_id=data[0], message_id=data[1]) if data else None

    # --- UNIFIED HANDLER (Единая точка входа) ---

    async def handle_callback(
        self, char_id: int, user_id: int, callback_data: InventoryCallback, state_data: dict
    ) -> InventoryViewDTO:
        """
        Главный метод обработки событий инвентаря.
        """
        if callback_data.action:
            await self._handle_action(char_id, callback_data)

            if callback_data.level == 2:
                return await self.get_item_list(
                    char_id,
                    user_id,
                    callback_data.section,
                    callback_data.category,
                    callback_data.page,
                    state_data,
                    callback_data.filter_type,
                )
            return await self.get_main_menu(char_id, user_id, state_data)

        if callback_data.level == 0:
            return await self.get_main_menu(char_id, user_id, state_data)

        elif callback_data.level == 1:
            return await self.get_item_list(
                char_id,
                user_id,
                callback_data.section,
                callback_data.category,
                callback_data.page,
                state_data,
                callback_data.filter_type,
            )

        elif callback_data.level == 2:
            if callback_data.item_id is None:
                return await self.get_main_menu(char_id, user_id, state_data)
            return await self.get_item_details(
                char_id,
                user_id,
                callback_data.item_id,
                callback_data.category,
                callback_data.page,
                callback_data.filter_type,
                state_data,
            )

        elif callback_data.level == 3 and callback_data.item_id:
            return await self.get_quick_slot_selection_menu(
                char_id, user_id, callback_data.item_id, callback_data.model_dump(), state_data
            )

        return await self.get_main_menu(char_id, user_id, state_data)

    async def _handle_action(self, char_id: int, cb: InventoryCallback):
        """Приватный обработчик действий."""
        if cb.action == "equip":
            await self._client.execute_action(char_id, "equip", item_id=cb.item_id, slot="auto")
        elif cb.action == "unequip":
            await self._client.execute_action(char_id, "unequip", item_id=cb.item_id)
        elif cb.action == "drop":
            await self._client.execute_action(char_id, "drop", item_id=cb.item_id)
        elif cb.action == "bind_quick_slot_select":
            await self._client.execute_action(char_id, "move_quick_slot", item_id=cb.item_id, position=cb.section)

    # --- SPECIFIC VIEW METHODS ---

    async def get_main_menu(self, char_id: int, user_id: int, state_data: dict) -> InventoryViewDTO:
        ui = self._get_ui(state_data, user_id)
        response: InventoryMainMenuResponseDTO = await self._client.get_view(char_id, "main")
        view = ui.render_main_menu(response.summary, response.equipped)
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
        ui = self._get_ui(state_data, user_id)
        response: InventoryBagResponseDTO = await self._client.get_view(
            char_id, "bag", section=section, category=category, page=page
        )
        view = ui.render_item_list(
            items_on_page=list(response.items),
            total_pages=response.total_pages,
            current_page=response.page,
            section=response.section,
            category=response.category or "all",
            filter_type=filter_type,
        )
        return InventoryViewDTO(content=view, current_page=response.page, total_pages=response.total_pages)

    async def get_item_details(
        self, char_id: int, user_id: int, item_id: int, category: str, page: int, filter_type: str, state_data: dict
    ) -> InventoryViewDTO:
        ui = self._get_ui(state_data, user_id)
        response: InventoryItemDetailsResponseDTO | None = await self._client.get_view(
            char_id, "details", item_id=item_id
        )

        if not response:
            return InventoryViewDTO(content=ViewResultDTO(text="Предмет не найден."))

        comparison_data = None
        if response.comparison:
            comparison_data = {"old_item_name": response.comparison.data.name, "diffs": {}, "is_empty": False}
        elif response.actions and "equip" in response.actions and not response.comparison:
            comparison_data = {"is_empty": True}

        view = ui.render_item_details(
            item=response.item, comparison_data=comparison_data, category=category, page=page, filter_type=filter_type
        )
        return InventoryViewDTO(content=view, item_id=item_id)

    async def get_quick_slot_selection_menu(
        self, char_id: int, user_id: int, item_id: int, context_data: dict, state_data: dict
    ) -> InventoryViewDTO:
        ui = self._get_ui(state_data, user_id)
        response: InventoryItemDetailsResponseDTO | None = await self._client.get_view(
            char_id, "details", item_id=item_id
        )

        if not response:
            return InventoryViewDTO(content=ViewResultDTO(text="Предмет не найден."))

        max_slots = await self._client.get_view(char_id, "quick_slot_limit")
        view = ui.render_quick_slot_selection_menu(response.item.data.name, item_id, max_slots, context_data)
        return InventoryViewDTO(content=view)

    # --- MISSING METHODS ---

    async def handle_quick_slot_action(
        self, char_id: int, user_id: int, item_id: int, action_key: str, slot_id: str | None, state_data: dict
    ) -> InventoryViewDTO:
        """
        Обрабатывает назначение предмета на быстрый слот.
        """
        if action_key == "bind" and slot_id:
            success, message = await self._client.execute_action(
                char_id, "move_quick_slot", item_id=item_id, position=slot_id
            )

        # После назначения возвращаемся в детали предмета
        # Для этого нам нужно знать категорию и страницу, но они могут быть потеряны
        # Поэтому возвращаемся в главное меню или пытаемся восстановить контекст
        return await self.get_main_menu(char_id, user_id, state_data)

    async def get_belt_overview(self, char_id: int, user_id: int, state_data: dict) -> InventoryViewDTO:
        """
        Показывает обзор пояса (быстрых слотов).
        """
        # Пока просто возвращаем главное меню, так как отдельного view для пояса нет в API
        return await self.get_main_menu(char_id, user_id, state_data)
