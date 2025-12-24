from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import get_character_stats_repo, get_inventory_repo
from apps.common.schemas_dto import (
    CombatSessionContainerDTO,
    InventoryItemDTO,
    ItemType,
    StatSourceData,
)
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.game_service.inventory.inventory_service import InventoryService
from apps.game_core.game_service.status.modifiers_calculator_service import (
    ModifiersCalculatorService,
)


class CombatAggregator:
    """
    Сервис для сбора и агрегации всех данных о персонаже, необходимых для боевой сессии.

    Собирает базовые статы, бонусы от экипировки, рассчитывает производные
    модификаторы и упаковывает все в `CombatSessionContainerDTO`.
    """

    def __init__(self, session: AsyncSession, account_manager: AccountManager):
        """
        Инициализирует сервис.

        Args:
            session: Сессия БД.
            account_manager: Менеджер аккаунта.
        """
        self.session = session
        self.account_manager = account_manager
        self.stats_repo = get_character_stats_repo(session)
        self.inv_repo = get_inventory_repo(session)
        log.debug("CombatAggregatorInit")

    async def collect_session_container(self, char_id: int) -> CombatSessionContainerDTO:
        """
        Собирает полный контейнер данных для боевой сессии персонажа.

        Args:
            char_id: ID персонажа.

        Returns:
            Заполненный `CombatSessionContainerDTO`.
        """
        log.info(f"CollectSessionContainer | event=start char_id={char_id}")
        container = CombatSessionContainerDTO(char_id=char_id, team="none", name="Unknown")

        try:
            base_stats = await self.stats_repo.get_stats(char_id)
            if not base_stats:
                log.warning(f"CollectSessionContainerFail | reason=no_base_stats char_id={char_id}")
                # Возвращаем пустой контейнер, чтобы не крашить вызывающий код
                return container

            equipped_items = await self.inv_repo.get_items_by_location(char_id, "equipped")
            inventory_items = await self.inv_repo.get_items_by_location(char_id, "inventory")
        except SQLAlchemyError:
            log.exception(f"CollectSessionContainerError | reason=db_error char_id={char_id}")
            return container

        # --- Слой 1: Базовые статы и производные от них ---
        for field, val in base_stats.model_dump().items():
            if isinstance(val, (int, float)):
                self._add_stat(container, field, float(val), "base")

        derived = ModifiersCalculatorService.calculate_all_modifiers_for_stats(base_stats)
        for field, val in derived.model_dump().items():
            if isinstance(val, (int, float)):
                self._add_stat(container, field, float(val), "base")
        log.debug(f"CollectSessionContainer | event=base_stats_processed char_id={char_id}")

        # --- Слой 2: Бонусы от экипировки ---
        self._process_equipment_bonuses(container, equipped_items)
        log.debug(f"CollectSessionContainer | event=equipment_processed char_id={char_id}")

        container.equipped_items = equipped_items

        # --- Слой 3: Предметы на поясе ---
        belt_items = [i for i in inventory_items if i.quick_slot_position]
        if belt_items:
            belt_items.sort(key=lambda x: x.quick_slot_position or "")
        container.belt_items = belt_items

        inv_service = InventoryService(self.session, char_id, self.account_manager)
        container.quick_slot_limit = await inv_service.get_quick_slot_limit()

        log.info(f"CollectSessionContainer | event=success char_id={char_id} stats_count={len(container.stats)}")
        return container

    def _process_equipment_bonuses(self, container: CombatSessionContainerDTO, items: list[InventoryItemDTO]) -> None:
        """Обрабатывает бонусы от экипированных предметов и добавляет их в контейнер."""
        for item in items:
            if item.item_type not in (ItemType.RESOURCE, ItemType.CURRENCY, ItemType.CONSUMABLE):
                if item.data.bonuses:
                    for stat_k, stat_v in item.data.bonuses.items():
                        self._add_stat(container, stat_k, float(stat_v), "equipment")

                if item.item_type == ItemType.WEAPON:
                    self._add_stat(container, "physical_damage_min", float(item.data.damage_min), "equipment")
                    self._add_stat(container, "physical_damage_max", float(item.data.damage_max), "equipment")

                if item.item_type == ItemType.ARMOR:
                    self._add_stat(container, "damage_reduction_flat", float(item.data.protection), "equipment")

    def _add_stat(
        self,
        container: CombatSessionContainerDTO,
        key: str,
        value: float,
        source_type: str,
    ) -> None:
        """
        Добавляет значение к указанной характеристике в контейнере из определенного источника.
        """
        if key not in container.stats:
            container.stats[key] = StatSourceData()

        target_source = container.stats[key]
        if source_type == "base":
            target_source.base += value
        elif source_type == "equipment":
            target_source.equipment += value
        elif source_type == "skills":
            target_source.skills += value
