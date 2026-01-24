from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.core.settings import settings
from backend.database.postgres.repositories import get_inventory_repo
from apps.common.schemas_dto import InventoryItemDTO
from apps.game_core.modules.inventory.Item.item_assembler import ItemAssembler
from backend.resources.game_data.items import get_random_base


class ItemDistributionService:
    """
    Сервис Распределения Предметов (Item Distribution Service).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.inventory_repo = get_inventory_repo(session)

    async def prepare_random_loot(self, tier: int, category_filter: str | None = None) -> InventoryItemDTO | None:
        """
        Создает случайный предмет и сохраняет его в 'generated_loot' у SYSTEM.
        """
        try:
            random_base = get_random_base(category_filter)
            base_id = random_base["id"]

            item_type, item_subtype, rarity_enum, item_data = ItemAssembler.assemble_equipment(
                base_id=base_id, target_tier=tier
            )

            item_id = await self.inventory_repo.create_item(
                character_id=settings.system_char_id,
                item_type=item_type,
                subtype=item_subtype,
                rarity=rarity_enum,
                item_data=item_data,
                location="generated_loot",
            )

            log.info(f"ItemDistribution | Generated system loot item_id={item_id} (Tier {tier})")
            return await self.inventory_repo.get_item_by_id(item_id)

        except ValueError as e:
            # Ошибка в данных (например, не найдена база) - это критично
            log.error(f"ItemDistribution | CRITICAL: Failed to assemble item. Invalid data? {e}")
            return None
        except Exception as e:  # noqa: BLE001
            # Другие ошибки (БД и т.д.) - логируем с трейсбеком
            log.exception(f"ItemDistribution | Failed to prepare random loot: {e}")
            return None

    async def prepare_specific_item(self, base_id: str, tier: int) -> InventoryItemDTO | None:
        """
        Создает КОНКРЕТНЫЙ предмет для награды за квест.
        """
        try:
            item_type, item_subtype, rarity_enum, item_data = ItemAssembler.assemble_equipment(
                base_id=base_id, target_tier=tier
            )

            item_id = await self.inventory_repo.create_item(
                character_id=settings.system_char_id,
                item_type=item_type,
                subtype=item_subtype,
                rarity=rarity_enum,
                item_data=item_data,
                location="quest_reward_buffer",
            )

            log.info(f"ItemDistribution | Prepared quest reward item_id={item_id}")
            return await self.inventory_repo.get_item_by_id(item_id)

        except ValueError as e:
            log.error(f"ItemDistribution | CRITICAL: Failed to assemble specific item. Invalid data? {e}")
            return None
        except Exception as e:  # noqa: BLE001
            log.exception(f"ItemDistribution | Failed to prepare specific item: {e}")
            return None

    async def issue_item_to_player(self, item_id: int, player_char_id: int) -> bool:
        """
        ФИНАЛИЗАЦИЯ: Передает предмет от Системы к Игроку.
        """
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item:
            log.error(f"ItemDistribution | Item {item_id} not found")
            return False

        if item.character_id != settings.system_char_id:
            log.warning(
                f"ItemDistribution | Security Warning: Item {item_id} is not owned by SYSTEM (owner={item.character_id})"
            )
            return False

        success = await self.inventory_repo.transfer_item(
            inventory_id=item_id, new_owner_id=player_char_id, new_location="inventory"
        )

        if success:
            log.info(f"ItemDistribution | Transferred item {item_id} to player {player_char_id}")
            return True
        else:
            log.error(f"ItemDistribution | DB Error transferring item {item_id}")
            return False

    async def recycle_declined_item(self, item_id: int) -> bool:
        """
        Если игрок отказался от лута.
        """
        log.info(f"ItemDistribution | Player declined item {item_id}. Recycling...")
        return await self.inventory_repo.delete_item(item_id)
