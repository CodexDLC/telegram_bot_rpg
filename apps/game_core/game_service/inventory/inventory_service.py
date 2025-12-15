from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import get_inventory_repo, get_wallet_repo
from apps.common.schemas_dto import EquippedSlot, InventoryItemDTO, ItemType, QuickSlot
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.game_service.matchmaking_service import MatchmakingService
from apps.game_core.game_service.stats_aggregation_service import StatsAggregationService

from .inventory_logic_helper import InventoryLogicHelpers

BASE_INVENTORY_SIZE = 20


class InventoryService:
    """
    Сервис для управления инвентарем и ресурсами игрока.

    Отвечает за получение, перемещение, экипировку предметов,
    а также за управление ресурсами (валюта, материалы).
    """

    def __init__(self, session: AsyncSession, char_id: int, account_manager: AccountManager):
        """
        Инициализирует сервис инвентаря.

        Args:
            session: Сессия БД.
            char_id: ID персонажа.
            account_manager: Менеджер аккаунта (для обновлений Redis).
        """
        self.session = session
        self.char_id = char_id
        self.account_manager = account_manager
        self.inventory_repo = get_inventory_repo(session)
        self.wallet_repo = get_wallet_repo(session)
        self.mm_service = MatchmakingService(session, self.account_manager)
        self.agg_service = StatsAggregationService(session)
        self.logic_helpers = InventoryLogicHelpers(inventory_repo=self.inventory_repo)
        log.debug(f"InventoryServiceInit | char_id={char_id}")

    async def get_item_by_id(self, item_id: int) -> InventoryItemDTO | None:
        """
        Получает предмет по его ID.

        Returns:
            DTO предмета или None, если не найден.
        """
        try:
            return await self.inventory_repo.get_item_by_id(item_id)
        except SQLAlchemyError as e:
            log.exception(f"GetItemError | item_id={item_id} char_id={self.char_id} error='{e}'")
            return None

    async def get_items(self, location: str = "inventory") -> list[InventoryItemDTO]:
        """
        Возвращает список предметов персонажа в указанной локации.

        Args:
            location: Локация предметов ('inventory', 'equipped', 'bank').
        """
        try:
            items = await self.inventory_repo.get_items_by_location(self.char_id, location)
            log.debug(f"GetItems | char_id={self.char_id} location='{location}' count={len(items)}")
            return items
        except SQLAlchemyError as e:
            log.exception(f"GetItemsError | char_id={self.char_id} location='{location}' error='{e}'")
            return []

    async def get_filtered_items(
        self, items: list[InventoryItemDTO], section: str, category: str | None = None
    ) -> list[InventoryItemDTO]:
        """
        Фильтрует и сортирует предметы для UI.

        Args:
            items: Исходный список предметов.
            section: Раздел инвентаря.
            category: Категория фильтрации (опционально).
        """
        return await self.logic_helpers.filter_and_sort_items(items=items, section=section, category=category)

    async def unbind_quick_slot(self, item_id: int) -> tuple[bool, str]:
        """
        Отвязывает предмет от быстрого слота.

        Returns:
            (Успех, Сообщение).
        """
        log.info(f"UnbindQuickSlotInit | char_id={self.char_id} item_id={item_id}")
        return await self.logic_helpers.unbind_quick_slot(item_id=item_id, char_id=self.char_id)

    async def get_quick_slot_limit(self) -> int:
        """
        Возвращает максимальное количество быстрых слотов персонажа.
        """
        return await self.logic_helpers.get_quick_slot_limit(char_id=self.char_id)

    async def add_resource(self, subtype: str, amount: int) -> None:
        """
        Добавляет ресурс персонажу.

        Args:
            subtype: Тип ресурса (например, 'gold', 'wood').
            amount: Количество.
        """
        group = self.logic_helpers.get_resource_group(subtype)
        try:
            await self.wallet_repo.add_resource(char_id=self.char_id, group=group, key=subtype, amount=amount)
            log.info(f"ResourceAdd | char_id={self.char_id} subtype='{subtype}' amount={amount}")
        except SQLAlchemyError as e:
            log.exception(f"ResourceAddError | char_id={self.char_id} subtype='{subtype}' amount={amount} error='{e}'")

    async def get_dust_amount(self) -> int:
        """Возвращает количество магической пыли у персонажа."""
        try:
            amount = await self.wallet_repo.get_resource_amount(
                char_id=self.char_id, group="currency", key="currency_dust"
            )
            log.debug(f"GetDust | char_id={self.char_id} amount={amount}")
            return amount
        except SQLAlchemyError as e:
            log.exception(f"GetDustError | char_id={self.char_id} error='{e}'")
            return 0

    async def consume_resource(self, subtype: str, amount: int) -> bool:
        """
        Списывает ресурс у персонажа.

        Returns:
            True, если списание прошло успешно.
        """
        group = self.logic_helpers.get_resource_group(subtype)
        try:
            success = await self.wallet_repo.remove_resource(
                char_id=self.char_id, group=group, key=subtype, amount=amount
            )
            log.info(f"ResourceConsume | char_id={self.char_id} subtype='{subtype}' amount={amount} success={success}")
            return success
        except SQLAlchemyError as e:
            log.exception(
                f"ResourceConsumeError | char_id={self.char_id} subtype='{subtype}' amount={amount} error='{e}'"
            )
            return False

    async def get_capacity(self) -> tuple[int, int]:
        """
        Рассчитывает текущую заполненность и максимальную вместимость инвентаря.

        Учитывает базовый размер и бонусы от характеристик/экипировки.

        Returns:
            (Текущее кол-во предметов, Максимальное кол-во слотов).
        """
        try:
            all_items = await self.inventory_repo.get_all_items(self.char_id)
            in_bag = [i for i in all_items if i.location == "inventory"]
            current_slots = len(in_bag)

            total_stats = await self.agg_service.get_character_total_stats(self.char_id)
            slots_bonus = 0
            if total_stats and "modifiers" in total_stats:
                modifiers = total_stats["modifiers"]
                if "inventory_slots_bonus" in modifiers:
                    slots_bonus = int(modifiers["inventory_slots_bonus"]["total"])

            max_slots = BASE_INVENTORY_SIZE + slots_bonus
            log.debug(f"GetCapacity | char_id={self.char_id} current={current_slots} max={max_slots}")
            return current_slots, max_slots
        except Exception as e:  # noqa: BLE001
            log.exception(f"GetCapacityError | char_id={self.char_id} error='{e}'")
            return 0, BASE_INVENTORY_SIZE

    async def has_free_slots(self, amount: int = 1) -> bool:
        """Проверяет, есть ли свободное место в инвентаре."""
        current, max_cap = await self.get_capacity()
        return (current + amount) <= max_cap

    async def equip_item(self, item_id: int, target_slot: EquippedSlot) -> tuple[bool, str]:
        """
        Экипирует предмет в указанный слот.

        Автоматически снимает предметы, занимающие этот слот (или конфликтующие слоты).
        """
        log.info(f"EquipItemInit | char_id={self.char_id} item_id={item_id} slot='{target_slot}'")
        try:
            item_to_equip = await self.inventory_repo.get_item_by_id(item_id)
            if not item_to_equip or item_to_equip.character_id != self.char_id:
                log.warning(f"EquipItemFail | reason=not_found char_id={self.char_id} item_id={item_id}")
                return False, "Предмет недоступен."

            if item_to_equip.item_type not in (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY):
                log.warning(
                    f"EquipItemFail | reason=invalid_type char_id={self.char_id} type='{item_to_equip.item_type}'"
                )
                return False, "Это нельзя надеть."

            await self._handle_slot_conflicts(item_to_equip, target_slot)

            update_data = {
                "location": "equipped",
                "equipped_slot": target_slot.value,
                "quick_slot_position": None,
            }
            if await self.inventory_repo.update_fields(item_id, update_data):
                await self.mm_service.refresh_gear_score(self.char_id)
                log.info(f"EquipItemSuccess | char_id={self.char_id} item_id={item_id}")
                return True, f"Надето: {item_to_equip.data.name} в {target_slot.name}"
            return False, "Ошибка БД."
        except SQLAlchemyError as e:
            log.exception(f"EquipItemError | char_id={self.char_id} item_id={item_id} error='{e}'")
            return False, "Ошибка базы данных."

    async def _handle_slot_conflicts(self, item_to_equip: InventoryItemDTO, target_slot: EquippedSlot):
        """Снимает предметы, конфликтующие с целевым слотом."""
        equipped_items = await self.inventory_repo.get_equipped_items(self.char_id)
        items_to_unequip = []

        # Логика двуручного оружия
        if target_slot in [EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND, EquippedSlot.TWO_HAND]:
            if target_slot == EquippedSlot.TWO_HAND:
                items_to_unequip.extend(
                    [i for i in equipped_items if i.equipped_slot in [EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND]]
                )
            else:
                items_to_unequip.extend([i for i in equipped_items if i.equipped_slot == EquippedSlot.TWO_HAND])

        # Прямой конфликт слотов
        items_to_unequip.extend([i for i in equipped_items if i.equipped_slot == target_slot])

        for item in items_to_unequip:
            await self.inventory_repo.move_item(item.inventory_id, "inventory")
            log.debug(f"AutoUnequip | char_id={self.char_id} item_id={item.inventory_id} reason=conflict")

    async def unequip_item(self, item_id: int) -> tuple[bool, str]:
        """Снимает предмет и возвращает его в инвентарь."""
        log.info(f"UnequipItemInit | char_id={self.char_id} item_id={item_id}")
        try:
            item = await self.inventory_repo.get_item_by_id(item_id)
            if not item or item.character_id != self.char_id:
                return False, "Ошибка."

            if await self.inventory_repo.move_item(item_id, "inventory"):
                await self.mm_service.refresh_gear_score(self.char_id)
                log.info(f"UnequipItemSuccess | char_id={self.char_id} item_id={item_id}")
                return True, f"Снято: {item.data.name}"
            return False, "Ошибка БД."
        except SQLAlchemyError as e:
            log.exception(f"UnequipItemError | char_id={self.char_id} item_id={item_id} error='{e}'")
            return False, "Ошибка базы данных."

    async def move_to_quick_slot(self, item_id: int, position: QuickSlot) -> tuple[bool, str]:
        """Назначает предмет на слот быстрого доступа."""
        log.info(f"QuickSlotBindInit | char_id={self.char_id} item_id={item_id} pos='{position}'")
        try:
            item = await self.inventory_repo.get_item_by_id(item_id)
            if not item or item.character_id != self.char_id:
                return False, "Предмет недоступен."

            if item.item_type != ItemType.CONSUMABLE or not item.data.is_quick_slot_compatible:
                return False, "Этот предмет нельзя поместить в быстрый слот."

            max_limit = await self.get_quick_slot_limit()
            target_pos_int = int(position.value.split("_")[-1])
            if target_pos_int > max_limit:
                return False, f"Слот недоступен. Лимит: {max_limit}."

            # Очистка слота, если занят
            items = await self.inventory_repo.get_all_items(self.char_id)
            for existing_item in items:
                if existing_item.quick_slot_position == position.value and existing_item.inventory_id != item_id:
                    await self.inventory_repo.update_fields(existing_item.inventory_id, {"quick_slot_position": None})
                    break

            update_data = {"quick_slot_position": position.value}
            if await self.inventory_repo.update_fields(item_id, update_data):
                log.info(f"QuickSlotBindSuccess | char_id={self.char_id} item_id={item_id}")
                return True, f"Предмет {item.data.name} закреплен за {position.name}."
            return False, "Ошибка БД."
        except SQLAlchemyError as e:
            log.exception(f"QuickSlotBindError | char_id={self.char_id} item_id={item_id} error='{e}'")
            return False, "Ошибка базы данных."
