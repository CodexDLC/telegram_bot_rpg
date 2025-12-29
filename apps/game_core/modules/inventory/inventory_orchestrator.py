from collections.abc import Sequence
from typing import Any

from apps.common.schemas_dto import EquippedSlot, QuickSlot
from apps.common.schemas_dto.inventory_dto import (
    InventoryBagResponseDTO,
    InventoryItemDetailsResponseDTO,
    InventoryMainMenuResponseDTO,
)
from apps.common.schemas_dto.item_dto import InventoryItemDTO
from apps.game_core.modules.inventory.logic.bag_logic import BagLogic
from apps.game_core.modules.inventory.logic.equipment_logic import EquipmentLogic
from apps.game_core.modules.inventory.logic.inventory_session_manager import InventorySessionManager
from apps.game_core.modules.inventory.logic.wallet_logic import WalletLogic


class InventoryOrchestrator:
    """
    Оркестратор инвентаря (Core Layer).
    Диспетчер логики. Принимает высокоуровневые команды (View/Action) и делегирует их
    специализированным модулям логики.
    """

    ITEMS_PER_PAGE = 10

    def __init__(self, session_manager: InventorySessionManager):
        self.session_manager = session_manager
        self.equip_logic = EquipmentLogic()
        self.bag_logic = BagLogic()
        self.wallet_logic = WalletLogic()

    # --- PUBLIC API (DISPATCHERS) ---

    async def get_view(self, char_id: int, view_type: str, **kwargs) -> Any:
        """
        Универсальный метод получения данных для отображения.
        :param view_type: 'main', 'bag', 'details'
        """
        if view_type == "main":
            return await self._get_main_menu_view(char_id)

        elif view_type == "bag":
            return await self._get_bag_view(
                char_id,
                section=kwargs.get("section", "inventory"),
                category=kwargs.get("category"),
                page=kwargs.get("page", 0),
            )

        elif view_type == "details":
            item_id = kwargs.get("item_id")
            if item_id is None:
                raise ValueError("item_id is required for details view")
            return await self._get_item_details_view(char_id, item_id=int(item_id))

        elif view_type == "quick_slot_limit":
            # Вспомогательный запрос для лимитов
            return await self._get_quick_slot_limit(char_id)

        else:
            raise ValueError(f"Unknown view_type: {view_type}")

    async def execute_action(self, char_id: int, action_type: str, **kwargs) -> tuple[bool, str]:
        """
        Универсальный метод выполнения действий.
        :param action_type: 'equip', 'unequip', 'drop', 'move_quick_slot'
        """
        item_id_raw = kwargs.get("item_id")
        if item_id_raw is None:
            return False, "Item ID is required"

        try:
            item_id = int(item_id_raw)
        except (ValueError, TypeError):
            return False, "Item ID must be an integer"

        if action_type == "equip":
            return await self._equip_item(char_id, item_id, slot_str=kwargs.get("slot", "auto"))

        elif action_type == "unequip":
            return await self._unequip_item(char_id, item_id)

        elif action_type == "drop":
            return await self._drop_item(char_id, item_id)

        elif action_type == "move_quick_slot":
            position = kwargs.get("position")
            if position is None:
                return False, "Position is required"
            return await self._move_to_quick_slot(char_id, item_id, position_str=str(position))

        else:
            return False, f"Unknown action: {action_type}"

    # --- PRIVATE METHODS (INTERNAL LOGIC) ---

    async def _get_main_menu_view(self, char_id: int) -> InventoryMainMenuResponseDTO:
        session = await self.session_manager.load_session(char_id)
        summary = self.wallet_logic.get_summary(session)
        equipped = self.equip_logic.get_equipped_items(session)
        return InventoryMainMenuResponseDTO(summary=summary, equipped=equipped)

    async def _get_bag_view(
        self, char_id: int, section: str, category: str | None, page: int = 0
    ) -> InventoryBagResponseDTO:
        session = await self.session_manager.load_session(char_id)

        all_items: Sequence[InventoryItemDTO]
        if section == "equip" and category and category != "all":
            try:
                slot = EquippedSlot(category)
                all_items = self.equip_logic.get_candidates_for_slot(session, slot)
                title = f"Выбор: {category}"
            except ValueError:
                all_items = self.bag_logic.get_items(session, section, category)
                title = "Инвентарь"
        else:
            all_items = self.bag_logic.get_items(session, section, category)
            title = "Инвентарь"

        total_items = len(all_items)
        total_pages = (total_items + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE

        if page < 0:
            page = 0
        if page >= total_pages and total_pages > 0:
            page = total_pages - 1

        start = page * self.ITEMS_PER_PAGE
        end = start + self.ITEMS_PER_PAGE
        items_on_page = list(all_items[start:end])

        return InventoryBagResponseDTO(
            items=items_on_page, page=page, total_pages=total_pages, section=section, category=category, title=title
        )

    async def _get_item_details_view(self, char_id: int, item_id: int) -> InventoryItemDetailsResponseDTO | None:
        session = await self.session_manager.load_session(char_id)
        item = session.items.get(item_id)
        if not item:
            return None

        actions = []
        comparison = None

        if item.location == "equipped":
            actions.append("unequip")
        else:
            actions.append("drop")
            if item.item_type in ("weapon", "armor", "accessory"):
                actions.append("equip")
                if hasattr(item.data, "valid_slots") and item.data.valid_slots:
                    target_slot_str = item.data.valid_slots[0]
                    for equipped in session.items.values():
                        if equipped.location == "equipped" and equipped.equipped_slot == target_slot_str:
                            comparison = equipped
                            break

            if item.item_type == "consumable":
                actions.append("use")
                if getattr(item.data, "is_quick_slot_compatible", False):
                    actions.append("quick_slot")

        return InventoryItemDetailsResponseDTO(item=item, actions=actions, comparison=comparison)

    async def _get_quick_slot_limit(self, char_id: int) -> int:
        return 4

    # --- ACTION IMPLEMENTATIONS ---

    async def _equip_item(self, char_id: int, item_id: int, slot_str: str | None = None) -> tuple[bool, str]:
        session = await self.session_manager.load_session(char_id)

        target_slot = None
        if slot_str and slot_str != "auto":
            try:
                target_slot = EquippedSlot(slot_str)
            except ValueError:
                return False, "Неверный слот."

        success, message = self.equip_logic.equip_item(session, item_id, target_slot)

        if success:
            await self.session_manager._save_session_to_redis(char_id, session)

        return success, message

    async def _unequip_item(self, char_id: int, item_id: int) -> tuple[bool, str]:
        session = await self.session_manager.load_session(char_id)

        if not self.wallet_logic.has_free_slots(session):
            return False, "Нет места в инвентаре."

        success, message = self.equip_logic.unequip_item(session, item_id)

        if success:
            item = session.items[item_id]
            await self.session_manager.update_item(char_id, item)

        return success, message

    async def _drop_item(self, char_id: int, item_id: int) -> tuple[bool, str]:
        session = await self.session_manager.load_session(char_id)
        success, message = self.bag_logic.drop_item(session, item_id)
        if success:
            await self.session_manager.remove_item(char_id, item_id)
        return success, message

    async def _move_to_quick_slot(self, char_id: int, item_id: int, position_str: str) -> tuple[bool, str]:
        session = await self.session_manager.load_session(char_id)
        try:
            position = QuickSlot(position_str)
        except ValueError:
            return False, "Неверный слот."

        success, message = self.bag_logic.move_to_quick_slot(session, item_id, position)
        if success:
            await self.session_manager._save_session_to_redis(char_id, session)
        return success, message
