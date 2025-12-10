# app/services/game_service/inventory/inventory_service.py

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import get_inventory_repo, get_wallet_repo
from apps.common.schemas_dto import EquippedSlot, InventoryItemDTO, ItemType, QuickSlot
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.game_service.matchmaking_service import MatchmakingService
from apps.game_core.game_service.stats_aggregation_service import StatsAggregationService

# 🔥 Импортируем новый класс-помощник
from .inventory_logic_helper import InventoryLogicHelpers

# Удалена: CONFLICT_MAP (перенесена в хелпер)
BASE_INVENTORY_SIZE = 20
BASE_QUICK_SLOT_LIMIT = 0


class InventoryService:
    """
    Сервис для управления инвентарем и ресурсами игрока.

    Layer 3: Фасад бизнес-логики. Оркестрирует работу с репозиториями,
    MatchmakingService и LogicHelpers.
    """

    def __init__(self, session: AsyncSession, char_id: int, account_manager: AccountManager):
        """
        Инициализирует InventoryService.
        """
        self.session = session
        self.char_id = char_id
        self.account_manager = account_manager
        # 🔥 Теперь репозитории инкапсулированы внутри сервиса
        self.inventory_repo = get_inventory_repo(session)
        self.wallet_repo = get_wallet_repo(session)
        self.mm_service = MatchmakingService(session, self.account_manager)
        self.agg_service = StatsAggregationService(session)  # Добавил для get_capacity

        # 🔥 Инициализация Logic Helper
        self.logic_helpers = InventoryLogicHelpers(inventory_repo=self.inventory_repo)

        log.debug(f"InventoryService | status=initialized char_id={char_id}")

    # =======================================================================
    # Layer 3 API (Публичный интерфейс для Layer 2)
    # =======================================================================

    async def get_item_by_id(self, item_id: int) -> InventoryItemDTO | None:
        """[Layer 3 API] Возвращает предмет по его ID."""
        log.debug(f"InventoryService | action=get_item_by_id item_id={item_id} char_id={self.char_id}")
        return await self.inventory_repo.get_item_by_id(item_id)

    async def unbind_quick_slot(self, item_id: int) -> tuple[bool, str]:
        """[Layer 3 API] Удаляет привязку предмета к Quick Slot."""
        # 🔥 Делегируем логику хелперу
        return await self.logic_helpers.unbind_quick_slot(item_id=item_id, char_id=self.char_id)

    async def get_filtered_items(
        self, items: list[InventoryItemDTO], section: str, category: str
    ) -> list[InventoryItemDTO]:
        """[Layer 3 API] Фильтрует список предметов по секции и категории/слоту."""
        # 🔥 Делегируем логику хелперу
        return await self.logic_helpers.get_filtered_items(items=items, section=section, category=category)

    async def get_quick_slot_limit(self) -> int:
        """[Layer 3 API] Возвращает максимальное количество доступных Quick Slots."""
        # 🔥 Делегируем логику хелперу
        return await self.logic_helpers.get_quick_slot_limit(char_id=self.char_id)

    # =======================================================================
    # ОСНОВНАЯ БИЗНЕС-ЛОГИКА (Использует Logic Helpers)
    # =======================================================================

    async def add_resource(self, subtype: str, amount: int) -> int:
        """Добавляет указанное количество ресурса в кошелек персонажа."""
        # 🔥 Используем статический метод хелпера
        group = InventoryLogicHelpers.map_subtype_to_group(subtype)
        new_total = await self.wallet_repo.add_resource(char_id=self.char_id, group=group, key=subtype, amount=amount)
        log.info(
            f"InventoryService | action=add_resource char_id={self.char_id} subtype='{subtype}' amount={amount} total={new_total}"
        )
        return new_total

    async def get_dust_amount(self) -> int:
        """Возвращает текущее количество ресурса "dust" в кошельке персонажа."""
        amount = await self.wallet_repo.get_resource_amount(char_id=self.char_id, group="currency", key="dust")
        log.debug(f"InventoryService | action=get_dust_amount char_id={self.char_id} amount={amount}")
        return amount

    async def consume_resource(self, subtype: str, amount: int) -> bool:
        """Удаляет указанное количество ресурса из кошелька персонажа."""
        # 🔥 Используем статический метод хелпера
        group = InventoryLogicHelpers.map_subtype_to_group(subtype)
        success = await self.wallet_repo.remove_resource(char_id=self.char_id, group=group, key=subtype, amount=amount)
        log.info(
            f"InventoryService | action=consume_resource char_id={self.char_id} subtype='{subtype}' amount={amount} success={success}"
        )
        return success

    async def get_capacity(self) -> tuple[int, int]:
        """Возвращает текущую занятость и максимальную вместимость инвентаря."""
        all_items = await self.inventory_repo.get_all_items(self.char_id)
        in_bag = [i for i in all_items if i.location == "inventory"]
        current_slots = len(in_bag)

        # 🔥 Используем инжектированный агрегатор
        total_stats = await self.agg_service.get_character_total_stats(self.char_id)

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
        """Проверяет, достаточно ли свободных слотов в инвентаре для N предметов."""
        current, max_cap = await self.get_capacity()
        has_space = (current + amount) <= max_cap
        log.debug(
            f"InventoryService | action=has_free_slots char_id={self.char_id} needed={amount} has_space={has_space}"
        )
        return has_space

    async def claim_item(self, item_id: int) -> bool:
        """Перемещает предмет из "мира" или другого источника в инвентарь персонажа."""
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
        """Экипирует предмет на персонажа, обрабатывая конфликты слотов."""
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
            # 🔥 Используем Logic Helper
            await self.logic_helpers.handle_slot_conflicts(item, target_slot)

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
        """Снимает экипированный предмет с персонажа и перемещает его в инвентарь."""
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
        """Удаляет предмет из инвентаря персонажа."""
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
        """Возвращает список предметов персонажа, находящихся в указанной локации."""
        items = await self.inventory_repo.get_items_by_location(self.char_id, location)
        log.debug(
            f"InventoryService | action=get_items char_id={self.char_id} location='{location}' count={len(items)}"
        )
        return items

    async def move_to_quick_slot(self, item_id: int, position: QuickSlot) -> tuple[bool, str]:
        """Привязывает CONSUMABLE к слоту быстрого доступа."""
        item = await self.inventory_repo.get_item_by_id(item_id)

        if not item or item.character_id != self.char_id:
            return False, "Предмет недоступен."

        if item.item_type != ItemType.CONSUMABLE:
            return False, "В быстрые слоты можно поместить только расходники."
        else:
            if not item.data.is_quick_slot_compatible:
                return False, "Этот расходник не предназначен для быстрого использования."

            # 🔥 Используем публичный API
            max_limit = await self.get_quick_slot_limit()
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
