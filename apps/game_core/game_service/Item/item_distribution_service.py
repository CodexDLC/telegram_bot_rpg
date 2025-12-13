from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.core.config import SYSTEM_CHAR_ID
from apps.common.database.repositories import get_inventory_repo
from apps.common.schemas_dto import InventoryItemDTO
from apps.game_core.game_service.Item.item_assembler import ItemAssembler
from apps.game_core.resources.game_data.items import get_random_base


class ItemDistributionService:
    """
    Сервис Распределения Предметов (Item Distribution Service).

    Отвечает за:
    1. Предварительную генерацию предметов на баланс Системы (Buffer).
    2. Отображение "потенциальной" награды (Preview).
    3. Трансфер предмета игроку по факту принятия решения (Claim).

    Используется в:
    - Боевой системе (генерация лута во время боя).
    - Квестовой системе (генерация награды при взятии квеста).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.inventory_repo = get_inventory_repo(session)

    async def prepare_random_loot(self, tier: int, category_filter: str | None = None) -> InventoryItemDTO | None:
        """
        Создает случайный предмет и сохраняет его в 'generated_loot' у SYSTEM.

        Args:
            tier: Целевой тир предмета.
            category_filter: Опционально 'melee_weapons', 'body_armor' и т.д.

        Returns:
            DTO предмета, который уже лежит в БД (у Системы), или None при ошибке.
        """
        try:
            # 1. Выбор базы
            random_base = get_random_base(category_filter)
            base_id = random_base["id"]

            # 2. Сборка (Assembler) - Чистая математика, без БД
            item_type, item_subtype, rarity_enum, item_data = ItemAssembler.assemble_equipment(
                base_id=base_id, target_tier=tier
            )

            # 3. Сохранение в буфер Системы
            # Предмет создается реальным, но игрок его еще не видит в своем инвентаре
            item_id = await self.inventory_repo.create_item(
                character_id=SYSTEM_CHAR_ID,
                item_type=item_type,
                subtype=item_subtype,
                rarity=rarity_enum,
                item_data=item_data,
                location="generated_loot",  # Специальный статус "Лут в ожидании"
            )

            log.info(f"ItemDistribution | Generated system loot item_id={item_id} (Tier {tier})")

            # Возвращаем DTO, чтобы UI мог отрисовать "Вам может выпасть: [Меч]"
            return await self.inventory_repo.get_item_by_id(item_id)

        except Exception as e:  # noqa: BLE001
            log.exception(f"ItemDistribution | Failed to prepare random loot: {e}")
            return None

    async def prepare_specific_item(self, base_id: str, tier: int) -> InventoryItemDTO | None:
        """
        Создает КОНКРЕТНЫЙ предмет для награды за квест.
        Пример: Квест дает "Стальной Меч". Мы создаем его заранее.
        """
        try:
            item_type, item_subtype, rarity_enum, item_data = ItemAssembler.assemble_equipment(
                base_id=base_id, target_tier=tier
            )

            item_id = await self.inventory_repo.create_item(
                character_id=SYSTEM_CHAR_ID,
                item_type=item_type,
                subtype=item_subtype,
                rarity=rarity_enum,
                item_data=item_data,
                location="quest_reward_buffer",  # Статус "Награда за квест"
            )

            log.info(f"ItemDistribution | Prepared quest reward item_id={item_id}")
            return await self.inventory_repo.get_item_by_id(item_id)

        except Exception as e:  # noqa: BLE001
            log.error(f"ItemDistribution | Failed to prepare specific item: {e}")
            return None

    async def issue_item_to_player(self, item_id: int, player_char_id: int) -> bool:
        """
        ФИНАЛИЗАЦИЯ: Передает предмет от Системы к Игроку.
        Вызывается, когда:
        - Игрок нажал "Забрать" в окне лута.
        - Игрок сдал квест и получает награду.
        """
        # 1. Проверяем, что предмет существует и принадлежит Системе
        item = await self.inventory_repo.get_item_by_id(item_id)
        if not item:
            log.error(f"ItemDistribution | Item {item_id} not found")
            return False

        if item.character_id != SYSTEM_CHAR_ID:
            log.warning(
                f"ItemDistribution | Security Warning: Item {item_id} is not owned by SYSTEM (owner={item.character_id})"
            )
            return False

        # 2. Трансфер
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
        Если игрок отказался от лута (нажал "Выбросить" или "Нет места").
        Предмет остается у Системы, но меняет статус на 'recycle_bin' или удаляется.
        В будущем тут будет логика возврата в Пул (Reuse).
        """
        # Пока просто удаляем, чтобы не засорять БД,
        # НО архитектурно мы готовы здесь сделать "pool_return"
        log.info(f"ItemDistribution | Player declined item {item_id}. Recycling...")
        return await self.inventory_repo.delete_item(item_id)
