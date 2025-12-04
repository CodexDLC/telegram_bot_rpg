from typing import cast

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.item_dto import EquippedSlot, InventoryItemDTO, ItemType, QuickSlot
from app.services.core_service.manager.account_manager import AccountManager
from app.services.game_service.matchmaking_service import MatchmakingService
from app.services.game_service.stats_aggregation_service import StatsAggregationService
from database.repositories import get_inventory_repo, get_wallet_repo
from database.repositories.ORM.wallet_repo import ResourceTypeGroup

CONFLICT_MAP: dict[EquippedSlot, list[EquippedSlot]] = {
    # Если надеваем двуручное оружие (TWO_HAND), оно занимает два слота.
    EquippedSlot.TWO_HAND: [EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND],
    # Если надеваем MAIN_HAND, оно конфликтует с двуручным оружием.
    EquippedSlot.MAIN_HAND: [EquippedSlot.TWO_HAND],
}

BASE_INVENTORY_SIZE = 20
BASE_QUICK_SLOT_LIMIT = 0


class InventoryService:
    """
    Сервис для управления инвентарем и ресурсами игрока.

    Предоставляет методы для добавления/удаления ресурсов, управления предметами
    (получение, экипировка, снятие, выбрасывание) и проверки вместимости инвентаря.
    """

    def __init__(self, session: AsyncSession, char_id: int, account_manager: AccountManager):
        """
        Инициализирует InventoryService.

        Args:
            session: Асинхронная сессия базы данных.
            char_id: Уникальный идентификатор персонажа.
            account_manager: Менеджер аккаунтов.
        """
        self.session = session
        self.char_id = char_id
        self.account_manager = account_manager
        self.inventory_repo = get_inventory_repo(session)
        self.wallet_repo = get_wallet_repo(session)
        self.mm_service = MatchmakingService(session, self.account_manager)
        log.debug(f"InventoryService | status=initialized char_id={char_id}")

    async def add_resource(self, subtype: str, amount: int) -> int:
        """
        Добавляет указанное количество ресурса в кошелек персонажа.
        """
        group = self._map_subtype_to_group(subtype)
        new_total = await self.wallet_repo.add_resource(char_id=self.char_id, group=group, key=subtype, amount=amount)
        log.info(
            f"InventoryService | action=add_resource char_id={self.char_id} subtype='{subtype}' amount={amount} total={new_total}"
        )
        return new_total

    async def get_dust_amount(self) -> int:
        """
        Возвращает текущее количество ресурса "dust" в кошельке персонажа.
        """
        amount = await self.wallet_repo.get_resource_amount(char_id=self.char_id, group="currency", key="dust")
        log.debug(f"InventoryService | action=get_dust_amount char_id={self.char_id} amount={amount}")
        return amount

    async def consume_resource(self, subtype: str, amount: int) -> bool:
        """
        Удаляет указанное количество ресурса из кошелька персонажа.
        """
        group = self._map_subtype_to_group(subtype)
        success = await self.wallet_repo.remove_resource(char_id=self.char_id, group=group, key=subtype, amount=amount)
        log.info(
            f"InventoryService | action=consume_resource char_id={self.char_id} subtype='{subtype}' amount={amount} success={success}"
        )
        return success

    async def get_capacity(self) -> tuple[int, int]:
        """
        Возвращает текущую занятость и максимальную вместимость инвентаря.
        """
        all_items = await self.inventory_repo.get_all_items(self.char_id)
        in_bag = [i for i in all_items if i.location == "inventory"]
        current_slots = len(in_bag)

        agg_service = StatsAggregationService(self.session)
        total_stats = await agg_service.get_character_total_stats(self.char_id)

        slots_bonus = 0
        if total_stats and "modifiers" in total_stats:
            mod_data = total_stats["modifiers"].get("inventory_slots_bonus")
            if mod_data:
                slots_bonus = int(mod_data.get("total", 0))

        max_slots = BASE_INVENTORY_SIZE + slots_bonus
        log.debug(
            f"InventoryService | action=get_capacity char_id={self.char_id} current={current_slots} max={max_slots}"
        )
        return current_slots, max_slots

    async def has_free_slots(self, amount: int = 1) -> bool:
        """
        Проверяет, достаточно ли свободных слотов в инвентаре для N предметов.
        """
        current, max_cap = await self.get_capacity()
        has_space = (current + amount) <= max_cap
        log.debug(
            f"InventoryService | action=has_free_slots char_id={self.char_id} needed={amount} has_space={has_space}"
        )
        return has_space

    async def claim_item(self, item_id: int) -> bool:
        """
        Перемещает предмет из "мира" или другого источника в инвентарь персонажа.
        """
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item:
            log.error(f"InventoryService | status=failed reason='Item not found' item_id={item_id}")
            return False

        success = await self.inventory_repo.transfer_item(
            inventory_id=item_id, new_owner_id=self.char_id, new_location="inventory"
        )

        if success:
            item_name = item.subtype if item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY) else item.data.name
            log.info(
                f"InventoryService | action=claim_item status=success char_id={self.char_id} item_id={item_id} name='{item_name}'"
            )
            return True
        log.warning(f"InventoryService | action=claim_item status=failed char_id={self.char_id} item_id={item_id}")
        return False

    async def equip_item(self, item_id: int, target_slot: EquippedSlot) -> tuple[bool, str]:
        """
        Экипирует предмет на персонажа, обрабатывая конфликты слотов.
        """
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item or item.character_id != self.char_id:
            log.warning(
                f"InventoryService | action=equip_item status=failed reason='Item not owned or not found' char_id={self.char_id} item_id={item_id}"
            )
            return False, "Предмет недоступен."

        if item.item_type not in (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY):
            log.warning(
                f"InventoryService | action=equip_item status=failed reason='Item type not equippable' char_id={self.char_id} item_id={item_id} type='{item.item_type}'"
            )
            return False, "Это нельзя надеть."
        else:
            await self._handle_slot_conflicts(item, target_slot)

            update_data = {
                "location": "equipped",
                "equipped_slot": target_slot.value,
                "quick_slot_position": None,
            }

            if await self.inventory_repo.update_fields(item_id, update_data):
                await self.mm_service.refresh_gear_score(self.char_id)
                log.info(
                    f"InventoryService | action=equip_item status=success char_id={self.char_id} item_id={item_id} slot='{target_slot.name}'"
                )
                return True, f"Надето: {item.data.name} в {target_slot.name}"

            log.error(
                f"InventoryService | action=equip_item status=failed reason='DB error in update_fields' char_id={self.char_id} item_id={item_id}"
            )
            return False, "Ошибка БД."

    async def unequip_item(self, item_id: int) -> tuple[bool, str]:
        """
        Снимает экипированный предмет с персонажа и перемещает его в инвентарь.
        """
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item or item.character_id != self.char_id:
            log.warning(
                f"InventoryService | action=unequip_item status=failed reason='Item not owned or not found' char_id={self.char_id} item_id={item_id}"
            )
            return False, "Ошибка."

        if item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
            return False, "Ресурсы не могут быть экипированы."
        else:
            if await self.inventory_repo.move_item(item_id, "inventory"):
                await self.mm_service.refresh_gear_score(self.char_id)
                log.info(
                    f"InventoryService | action=unequip_item status=success char_id={self.char_id} item_id={item_id} name='{item.data.name}'"
                )
                return True, f"Снято: {item.data.name}"

            log.error(
                f"InventoryService | action=unequip_item status=failed reason='DB error moving item' char_id={self.char_id} item_id={item_id}"
            )
            return False, "Ошибка БД."

    async def drop_item(self, item_id: int) -> bool:
        """
        Удаляет предмет из инвентаря персонажа.
        """
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item or item.character_id != self.char_id:
            log.warning(
                f"InventoryService | action=drop_item status=failed reason='Item not owned or not found' char_id={self.char_id} item_id={item_id}"
            )
            return False

        if item.location == "equipped":
            await self.inventory_repo.move_item(item_id, "inventory")
            log.debug(
                f"InventoryService | action=drop_item reason='Unequipped before dropping' char_id={self.char_id} item_id={item_id}"
            )

        success = await self.inventory_repo.delete_item(item_id)
        log.info(f"InventoryService | action=drop_item status={success} char_id={self.char_id} item_id={item_id}")
        return success

    async def get_items(self, location: str = "inventory") -> list[InventoryItemDTO]:
        """
        Возвращает список предметов персонажа, находящихся в указанной локации.
        """
        items = await self.inventory_repo.get_items_by_location(self.char_id, location)
        log.debug(
            f"InventoryService | action=get_items char_id={self.char_id} location='{location}' count={len(items)}"
        )
        return items

    def _map_subtype_to_group(self, subtype: str) -> ResourceTypeGroup:
        """
        Определяет группу ресурсов для `WalletRepo` на основе подтипа.
        """
        mapping = {
            "currency": ("dust", "shard", "core"),
            "ores": ("ore", "ingot", "stone"),
            "leathers": ("leather", "hide", "skin"),
            "fabrics": ("cloth", "fiber"),
            "organics": ("herb", "food", "meat"),
        }

        for group, keywords in mapping.items():
            if any(keyword in subtype for keyword in keywords):
                return cast(ResourceTypeGroup, group)

        return "parts"

    async def _get_equipped_map(self) -> dict[EquippedSlot, InventoryItemDTO]:
        """
        Получает все экипированные предметы и преобразует их в словарь
        для быстрого поиска по EquippedSlot.
        """
        equipped_items = await self.get_items("equipped")
        equipped_map = {EquippedSlot(item.equipped_slot): item for item in equipped_items if item.equipped_slot}
        log.debug(f"InventoryService | action=get_equipped_map count={len(equipped_map)}")
        return equipped_map

    async def _handle_slot_conflicts(self, new_item: InventoryItemDTO, target_slot: EquippedSlot) -> None:
        """
        Снимает предметы, конфликтующие с целевым слотом.
        """
        equipped_map = await self._get_equipped_map()
        items_to_unequip: list[InventoryItemDTO] = []

        if target_slot in equipped_map:
            items_to_unequip.append(equipped_map[target_slot])

        slots_to_check = CONFLICT_MAP.get(target_slot, [])
        for conflict_slot in slots_to_check:
            if conflict_slot in equipped_map:
                items_to_unequip.append(equipped_map[conflict_slot])

        for old_item in set(items_to_unequip):
            if old_item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
                continue
            else:
                await self.inventory_repo.update_fields(
                    old_item.inventory_id, {"location": "inventory", "equipped_slot": None, "quick_slot_position": None}
                )
                log.info(f"Конфликт разрешен: снят {old_item.data.name} из {old_item.equipped_slot}.")

    async def _get_quick_slot_limit(self) -> int:
        """
        Рассчитывает максимальное количество доступных Quick Slots.
        """
        equipped_map = await self._get_equipped_map()
        belt_item = equipped_map.get(EquippedSlot.BELT_ACCESSORY)

        if not belt_item or belt_item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
            return BASE_QUICK_SLOT_LIMIT
        else:
            current_limit = 0
            if belt_item.data.bonuses:
                capacity = belt_item.data.bonuses.get("quick_slot_capacity", 0)
                if isinstance(capacity, (int, float)):
                    current_limit = int(capacity)

            final_limit = max(BASE_QUICK_SLOT_LIMIT, current_limit)
            log.info(f"QuickSlot | calculated_limit={final_limit} belt='{belt_item.data.name}'")
            return final_limit

    async def move_to_quick_slot(self, item_id: int, position: QuickSlot) -> tuple[bool, str]:
        """
        Привязывает CONSUMABLE к слоту быстрого доступа.
        """
        item = await self.inventory_repo.get_item_by_id(item_id)

        if not item or item.character_id != self.char_id:
            return False, "Предмет недоступен."

        if item.item_type != ItemType.CONSUMABLE:
            return False, "В быстрые слоты можно поместить только расходники."
        else:
            if not item.data.is_quick_slot_compatible:
                return False, "Этот расходник не предназначен для быстрого использования."

            max_limit = await self._get_quick_slot_limit()
            target_pos_int = int(position.value.split("_")[-1])

            if target_pos_int > max_limit:
                return False, f"Слот {position.name} ({target_pos_int}) недоступен. Лимит {max_limit} слотов."

            equipped_items = await self.inventory_repo.get_items_by_location(self.char_id, "inventory")
            for existing_item in equipped_items:
                if existing_item.quick_slot_position == position.value and existing_item.inventory_id != item_id:
                    await self.inventory_repo.update_fields(existing_item.inventory_id, {"quick_slot_position": None})
                    log.info(
                        f"QuickSlot | action=cleared_slot char_id={self.char_id} old_item_id={existing_item.inventory_id}"
                    )
                    break

            update_data = {
                "location": "inventory",
                "quick_slot_position": position.value,
                "equipped_slot": None,
            }

            if await self.inventory_repo.update_fields(item_id, update_data):
                log.info(
                    f"QuickSlot | action=assigned char_id={self.char_id} item_id={item_id} position={position.name}"
                )
                return True, f"Предмет {item.data.name} закреплен за {position.name}."

            return False, "Ошибка при сохранении в БД."
