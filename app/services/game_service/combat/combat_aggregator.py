from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.combat_source_dto import (
    CombatSessionContainerDTO,
    StatSourceData,
)
from app.resources.schemas_dto.item_dto import InventoryItemDTO, ItemType
from app.services.game_service.modifiers_calculator_service import (
    ModifiersCalculatorService,
)
from database.repositories import get_character_stats_repo, get_inventory_repo


class CombatAggregator:
    """
    Собирает все данные о персонаже, необходимые для боя, в единый контейнер.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует агрегатор.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session
        self.stats_repo = get_character_stats_repo(session)
        self.inv_repo = get_inventory_repo(session)
        log.debug("CombatAggregatorInit | status=initialized")

    async def collect_session_container(self, char_id: int) -> CombatSessionContainerDTO:
        """
        Собирает полный контейнер данных для боевой сессии персонажа.
        (ОРКЕСТРАТОР)

        Args:
            char_id: ID персонажа.

        Returns:
            Заполненный контейнер данных.
        """
        log.info(f"CollectSessionContainerStart | char_id={char_id}")
        container = CombatSessionContainerDTO(char_id=char_id, team="none", name="Unknown")

        # 1. Загрузка данных
        base_stats = await self.stats_repo.get_stats(char_id)
        items = await self.inv_repo.get_items_by_location(char_id, "equipped")

        # 2. Обработка базовых и производных статов
        if base_stats:
            for field, val in base_stats.model_dump().items():
                if isinstance(val, (int, float)):
                    self._add_stat(container, field, float(val), "base")

            derived = ModifiersCalculatorService.calculate_all_modifiers_for_stats(base_stats)
            for field, val in derived.model_dump().items():
                if isinstance(val, (int, float)):
                    self._add_stat(container, field, float(val), "base")

            log.debug(f"BaseStatsCollected | char_id={char_id}")

        # 3. Обработка экипировки
        has_weapon = self._process_equipment_bonuses(container, items)
        log.debug(f"EquipmentModifiersApplied | char_id={char_id}")

        # 4. Расчет урона для кулачного боя (если нет оружия)
        if not has_weapon:
            self._calculate_unarmed_damage(container)

        # 🔥 ИСПРАВЛЕНИЕ: ПРАВИЛЬНОЕ присвоение equipped_items
        container.equipped_items = items

        log.info(f"CollectSessionContainerSuccess | char_id={char_id} final_stats_count={len(container.stats)}")
        return container

    def _process_equipment_bonuses(self, container: CombatSessionContainerDTO, items: list[InventoryItemDTO]) -> bool:
        """
        Обрабатывает бонусы от экипированных предметов и проверяет наличие оружия.
        """
        has_weapon = False
        for item in items:
            if item.item_type == ItemType.WEAPON:
                has_weapon = True

            # Бонусы предмета (bonuses dict)
            if item.data.bonuses:
                for stat_k, stat_v in item.data.bonuses.items():
                    self._add_stat(container, stat_k, float(stat_v), "equipment")

            # Базовые свойства оружия (урон)
            if item.item_type == ItemType.WEAPON and hasattr(item.data, "damage_min"):
                self._add_stat(container, "physical_damage_min", float(item.data.damage_min), "equipment")
                self._add_stat(container, "physical_damage_max", float(item.data.damage_max), "equipment")

            # Базовые свойства брони (защита)
            if item.item_type == ItemType.ARMOR and hasattr(item.data, "protection"):
                self._add_stat(container, "damage_reduction_flat", float(item.data.protection), "equipment")

        return has_weapon

    def _calculate_unarmed_damage(self, container: CombatSessionContainerDTO) -> None:
        """
        Рассчитывает и добавляет урон от кулачного боя на основе Силы.
        """
        str_data = container.stats.get("strength")
        strength_val = str_data.base if str_data else 0.0

        base_min, base_max = 1, 3
        added_max = strength_val * 1.0
        added_min = strength_val // 3
        final_min = int(base_min + added_min)
        final_max = int(base_max + added_max)

        self._add_stat(container, "physical_damage_min", float(final_min), "equipment")
        self._add_stat(container, "physical_damage_max", float(final_max), "equipment")

        log.debug(
            f"UnarmedDamageCalculated | char_id={container.char_id} strength={strength_val} damage_min={final_min} damage_max={final_max}"
        )

    def _add_stat(
        self,
        container: CombatSessionContainerDTO,
        key: str,
        value: float,
        source_type: str,
    ) -> None:
        """
        Добавляет значение к стату в контейнере.
        ...
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
