import random

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.postgres.repositories import get_inventory_repo, get_wallet_repo
from apps.common.schemas_dto import ItemType
from apps.game_core.modules.inventory.inventory_logic_helper import InventoryLogicHelpers
from backend.resources.game_data.items import get_bundle_by_id

# Настройки экономики
BASE_DUST_PER_TIER = 10
ESSENCE_EXTRACT_CHANCE = 0.7
ESSENCE_RETURN_RATIO = 0.3


class DismantleService:
    """
    Сервис Разбора (Destruction Layer).
    """

    def __init__(self, session: AsyncSession):
        self.inventory_repo = get_inventory_repo(session)
        self.wallet_repo = get_wallet_repo(session)

    async def dismantle_item(self, char_id: int, item_id: int) -> dict[str, int]:
        """
        Разбирает предмет и возвращает ресурсы.
        """
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item or item.character_id != char_id:
            return {}

        if item.item_type in (ItemType.RESOURCE, ItemType.CURRENCY):
            return {}

        rewards = {}

        # Расчет пыли
        tier_approx = max(1, int(item.data.base_price / 15))
        dust_amount = int(BASE_DUST_PER_TIER * tier_approx * random.uniform(0.9, 1.1))
        rewards["currency_dust"] = dust_amount

        # Расчет эссенций
        if item.data.components and item.data.components.essence_id:
            essence_ids = item.data.components.essence_id
            if isinstance(essence_ids, str):  # Обратная совместимость, если в БД еще остались строки
                essence_ids = [eid.strip() for eid in essence_ids.split(",")]

            for essence_id in essence_ids:
                bundle_data = get_bundle_by_id(essence_id)
                if bundle_data and random.random() < ESSENCE_EXTRACT_CHANCE:
                    ingredient_id = bundle_data["ingredient_id"]
                    rewards[ingredient_id] = rewards.get(ingredient_id, 0) + 1

        # Расчет материалов
        if item.data.components and item.data.components.material_id:
            mat_id = item.data.components.material_id
            if random.random() < 0.25:
                rewards[mat_id] = 1

        # Транзакция
        if await self.inventory_repo.delete_item(item_id):
            for key, amount in rewards.items():
                wallet_group = InventoryLogicHelpers.get_resource_group(key)
                await self.wallet_repo.add_resource(char_id, wallet_group, key, amount)

            log.info(f"Dismantle | User {char_id} -> {rewards}")
            return rewards

        return {}
