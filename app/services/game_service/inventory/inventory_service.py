from typing import cast

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.item_dto import InventoryItemDTO, ItemType
from app.services.core_service.manager.account_manager import AccountManager
from app.services.game_service.matchmaking_service import MatchmakingService
from app.services.game_service.stats_aggregation_service import StatsAggregationService
from database.repositories import get_inventory_repo, get_wallet_repo
from database.repositories.ORM.wallet_repo import ResourceTypeGroup

BASE_INVENTORY_SIZE = 20


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

        Args:
            subtype: Подтип ресурса (например, "dust", "ore").
            amount: Количество ресурса для добавления.

        Returns:
            Новое общее количество ресурса в кошельке.
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

        Returns:
            Количество "dust".
        """
        amount = await self.wallet_repo.get_resource_amount(char_id=self.char_id, group="currency", key="dust")
        log.debug(f"InventoryService | action=get_dust_amount char_id={self.char_id} amount={amount}")
        return amount

    async def consume_resource(self, subtype: str, amount: int) -> bool:
        """
        Удаляет указанное количество ресурса из кошелька персонажа.

        Args:
            subtype: Подтип ресурса.
            amount: Количество ресурса для удаления.

        Returns:
            True, если ресурс успешно удален, иначе False.
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

        Максимальная вместимость рассчитывается с учетом базового размера
        и бонусов от характеристик персонажа (например, Perception).

        Returns:
            Кортеж `(current_slots, max_slots)`, где `current_slots` —
            количество занятых слотов, а `max_slots` — общая вместимость.
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

        Args:
            amount: Количество предметов, для которых нужно проверить наличие места.

        Returns:
            True, если есть достаточно свободных слотов, иначе False.
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

        Args:
            item_id: Уникальный идентификатор предмета.

        Returns:
            True, если предмет успешно получен, иначе False.
        """
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item:
            log.error(f"InventoryService | status=failed reason='Item not found' item_id={item_id}")
            return False

        success = await self.inventory_repo.transfer_item(
            inventory_id=item_id, new_owner_id=self.char_id, new_location="inventory"
        )

        if success:
            log.info(
                f"InventoryService | action=claim_item status=success char_id={self.char_id} item_id={item_id} name='{item.data.name}'"
            )
            return True
        log.warning(f"InventoryService | action=claim_item status=failed char_id={self.char_id} item_id={item_id}")
        return False

    async def equip_item(self, item_id: int) -> tuple[bool, str]:
        """
        Экипирует предмет на персонажа.

        Обрабатывает конфликты слотов (автоматически снимает старые предметы).
        Обновляет Gear Score персонажа после экипировки.

        Args:
            item_id: Уникальный идентификатор предмета для экипировки.

        Returns:
            Кортеж `(bool, str)`, где `bool` указывает на успешность экипировки,
            а `str` содержит соответствующее сообщение.
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

        await self._handle_slot_conflicts(item)

        if await self.inventory_repo.move_item(item_id, "equipped"):
            await self.mm_service.refresh_gear_score(self.char_id)
            log.info(
                f"InventoryService | action=equip_item status=success char_id={self.char_id} item_id={item_id} name='{item.data.name}'"
            )
            return True, f"Надето: {item.data.name}"

        log.error(
            f"InventoryService | action=equip_item status=failed reason='DB error moving item' char_id={self.char_id} item_id={item_id}"
        )
        return False, "Ошибка БД."

    async def unequip_item(self, item_id: int) -> tuple[bool, str]:
        """
        Снимает экипированный предмет с персонажа и перемещает его в инвентарь.

        Обновляет Gear Score персонажа после снятия.

        Args:
            item_id: Уникальный идентификатор предмета для снятия.

        Returns:
            Кортеж `(bool, str)`, где `bool` указывает на успешность снятия,
            а `str` содержит соответствующее сообщение.
        """
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item or item.character_id != self.char_id:
            log.warning(
                f"InventoryService | action=unequip_item status=failed reason='Item not owned or not found' char_id={self.char_id} item_id={item_id}"
            )
            return False, "Ошибка."

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

        Если предмет был экипирован, он сначала перемещается в инвентарь,
        а затем удаляется.

        Args:
            item_id: Уникальный идентификатор предмета для удаления.

        Returns:
            True, если предмет успешно удален, иначе False.
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

        Args:
            location: Локация предметов (например, "inventory", "equipped").

        Returns:
            Список DTO `InventoryItemDTO`.
        """
        items = await self.inventory_repo.get_items_by_location(self.char_id, location)
        log.debug(
            f"InventoryService | action=get_items char_id={self.char_id} location='{location}' count={len(items)}"
        )
        return items

    def _map_subtype_to_group(self, subtype: str) -> ResourceTypeGroup:
        """
        Определяет группу ресурсов для `WalletRepo` на основе подтипа.

        Args:
            subtype: Подтип ресурса.

        Returns:
            Группа ресурсов (`ResourceTypeGroup`).
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

    async def _handle_slot_conflicts(self, new_item: InventoryItemDTO) -> None:
        """
        Автоматически снимает экипированные предметы, если они конфликтуют
        со слотами нового предмета.

        Args:
            new_item: Новый предмет, который будет экипирован.
        """
        if new_item.item_type not in (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY):
            return

        required_slots = set(new_item.data.valid_slots)  # type: ignore[union-attr]
        equipped = await self.inventory_repo.get_items_by_location(self.char_id, "equipped")

        for old in equipped:
            if old.item_type not in (ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY):
                continue

            old_slots = set(old.data.valid_slots)  # type: ignore[union-attr]

            if not required_slots.isdisjoint(old_slots):
                await self.unequip_item(old.inventory_id)
                log.debug(
                    f"InventoryService | action=unequip_conflict char_id={self.char_id} old_item_id={old.inventory_id} new_item_id={new_item.inventory_id}"
                )
