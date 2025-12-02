# app/services/game_service/combat/combat_aggregator.py
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.combat_source_dto import (
    CombatSessionContainerDTO,
    StatSourceData,
)
from app.resources.schemas_dto.item_dto import ItemType
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
            session (AsyncSession): Асинхронная сессия SQLAlchemy.
        """
        self.session = session
        self.stats_repo = get_character_stats_repo(session)
        self.inv_repo = get_inventory_repo(session)
        log.debug("CombatAggregator инициализирован.")

    async def collect_session_container(self, char_id: int) -> CombatSessionContainerDTO:
        """
        Собирает полный контейнер данных для боевой сессии персонажа.

        Процесс сбора:
        1. Загружает базовые и производные статы из БД.
        2. Добавляет модификаторы от экипированных предметов.
        3. Рассчитывает урон для кулачного боя, если оружие не экипировано.

        Args:
            char_id (int): ID персонажа.

        Returns:
            CombatSessionContainerDTO: Заполненный контейнер данных.
        """
        log.debug(f"Начало сбора данных для боевого контейнера char_id={char_id}")
        container = CombatSessionContainerDTO(char_id=char_id, team="none", name="Unknown")

        # 1. Базовые статы (БД) + Модификаторы
        base_stats = await self.stats_repo.get_stats(char_id)
        if base_stats:
            # Заполняем базу
            for field, val in base_stats.model_dump().items():
                if isinstance(val, (int, float)):
                    self._add_stat(container, field, float(val), "base")

            # Считаем производные (HP, Crit и т.д.)
            derived = ModifiersCalculatorService.calculate_all_modifiers_for_stats(base_stats)
            for field, val in derived.model_dump().items():
                if isinstance(val, (int, float)):
                    self._add_stat(container, field, float(val), "base")

            log.debug(f"Базовые и производные статы для char_id={char_id} собраны.")

        # 2. Экипировка
        items = await self.inv_repo.get_items_by_location(char_id, "equipped")
        has_weapon = False
        log.debug(f"Найдено {len(items)} экипированных предметов для char_id={char_id}.")

        for item in items:
            if item.item_type == ItemType.WEAPON:
                has_weapon = True

            # Бонусы предмета (bonuses dict)
            if item.data.bonuses:
                for stat_k, stat_v in item.data.bonuses.items():
                    self._add_stat(container, stat_k, float(stat_v), "equipment")

            # Базовые свойства оружия (урон)
            if item.item_type == ItemType.WEAPON and hasattr(item.data, "damage_min"):
                self._add_stat(
                    container,
                    "physical_damage_min",
                    float(item.data.damage_min),
                    "equipment",
                )
                self._add_stat(
                    container,
                    "physical_damage_max",
                    float(item.data.damage_max),
                    "equipment",
                )

            # Базовые свойства брони (защита)
            if item.item_type == ItemType.ARMOR and hasattr(item.data, "protection"):
                self._add_stat(
                    container,
                    "damage_reduction_flat",
                    float(item.data.protection),
                    "equipment",
                )
        log.debug(f"Модификаторы от экипировки для char_id={char_id} применены.")

        # 3. Кулачный бой (UNARMED), если нет оружия
        # 3. Кулачный бой (UNARMED)
        if not has_weapon:
            str_data = container.stats.get("strength")
            strength_val = str_data.base if str_data else 0.0

            # === НОВАЯ ФОРМУЛА ===
            # Базовый разброс (даже для слабака с 0 силы)
            base_min = 1
            base_max = 3

            # Бонус от Силы
            # Макс: +1 за каждую 1 силу
            # Мин: +1 за каждые 3 силы
            added_max = strength_val * 1.0
            added_min = strength_val // 3

            final_min = int(base_min + added_min)
            final_max = int(base_max + added_max)

            self._add_stat(container, "physical_damage_min", float(final_min), "equipment")
            self._add_stat(container, "physical_damage_max", float(final_max), "equipment")

            log.debug(f"👊 Unarmed: Str={strength_val} -> Dmg {final_min}-{final_max}")

        log.debug(f"Сбор данных для char_id={char_id} завершен. Контейнер: {container.model_dump_json(indent=2)}")
        return container

    def _add_stat(
        self,
        container: CombatSessionContainerDTO,
        key: str,
        value: float,
        source_type: str,
    ) -> None:
        """
        Добавляет значение к стату в контейнере.

        Args:
            container (CombatSessionContainerDTO): Контейнер данных.
            key (str): Название стата (например, 'strength').
            value (float): Значение для добавления.
            source_type (str): Источник ('base', 'equipment', 'skills').

        Returns:
            None
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
        # Нет логгирования, т.к. это слишком "шумный" внутренний метод
