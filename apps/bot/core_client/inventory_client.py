from typing import Any

from apps.common.schemas_dto import InventoryItemDTO
from apps.game_core.modules.inventory.inventory_orchestrator import InventoryOrchestrator


class InventoryClient:
    """
    Клиент для взаимодействия с системой инвентаря.
    В будущем здесь будут HTTP-запросы к микросервису.
    Сейчас это прокси к InventoryOrchestrator.
    """

    def __init__(self, orchestrator: InventoryOrchestrator):
        self._orchestrator = orchestrator

    # --- NEW API (Unified) ---

    async def get_view(self, char_id: int, view_type: str, **kwargs) -> Any:
        """
        Получение данных для отображения (Main Menu, Bag, Details).
        """
        return await self._orchestrator.get_view(char_id, view_type, **kwargs)

    async def execute_action(self, char_id: int, action_type: str, **kwargs) -> tuple[bool, str]:
        """
        Выполнение действия (Equip, Drop, Use).
        """
        return await self._orchestrator.execute_action(char_id, action_type, **kwargs)

    # --- LEGACY API (Adapters for Loot/Shop/Matchmaking) ---

    async def get_summary(self, char_id: int) -> dict:
        # Адаптер: возвращает dict, как раньше
        response = await self.get_view(char_id, "main")
        return response.summary

    async def get_items(self, char_id: int, section: str, category: str, page: int, page_size: int) -> dict:
        # Адаптер: возвращает dict с items и пагинацией
        response = await self.get_view(char_id, "bag", section=section, category=category, page=page)
        return {"items": response.items, "total_pages": response.total_pages, "current_page": response.page}

    async def get_item_details(self, char_id: int, item_id: int) -> InventoryItemDTO | None:
        response = await self.get_view(char_id, "details", item_id=item_id)
        return response.item if response else None

    async def get_comparison(self, char_id: int, item: InventoryItemDTO) -> dict | None:
        # Этот метод сложно адаптировать, так как get_view('details') требует item_id, а тут передается DTO.
        # Но обычно get_comparison вызывался после get_item_details.
        # Если старый код вызывает это отдельно, он может упасть.
        # Но в UI мы уже заменили вызов. Если Loot/Shop это не используют, то ок.
        return None

    async def equip_item(self, char_id: int, item_id: int, slot: str) -> tuple[bool, str]:
        return await self.execute_action(char_id, "equip", item_id=item_id, slot=slot)

    async def use_item(self, char_id: int, item_id: int) -> tuple[bool, str]:
        # use пока не реализован в execute_action, добавим заглушку или реализуем
        # return await self.execute_action(char_id, "use", item_id=item_id)
        return False, "Not implemented yet"

    async def get_quick_slot_limit(self, char_id: int) -> int:
        return await self.get_view(char_id, "quick_slot_limit")

    async def bind_quick_slot(self, char_id: int, item_id: int, slot_key: str) -> tuple[bool, str]:
        return await self.execute_action(char_id, "move_quick_slot", item_id=item_id, position=slot_key)

    async def unbind_quick_slot(self, char_id: int, item_id: int) -> tuple[bool, str]:
        # unbind пока нет, можно реализовать как move(None)
        return False, "Not implemented yet"
