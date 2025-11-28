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
            for field in base_stats.model_fields:
                val = getattr(base_stats, field)
                if isinstance(val, (int, float)):
                    self._add_stat(container, field, float(val), "base")

            # Считаем производные (HP, Crit и т.д.)
            derived = ModifiersCalculatorService.calculate_all_modifiers_for_stats(base_stats)
            for field in derived.model_fields:
                val = getattr(derived, field)
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
        if not has_weapon:
            # Формула: 1 + (Strength * 0.5)
            # Берем силу из контейнера, которую мы только что положили в шаге 1
            strength = container.stats.get("strength", StatSourceData()).base
            unarmed_dmg = 1.0 + (strength * 0.5)

            # Добавляем как "equipment" (виртуальное оружие)
            self._add_stat(container, "physical_damage_min", int(unarmed_dmg), "equipment")
            self._add_stat(container, "physical_damage_max", int(unarmed_dmg + 2), "equipment")  # Разброс 1-3
            log.debug(
                f"Оружие не найдено, для char_id={char_id} рассчитан урон без оружия: {unarmed_dmg}-{unarmed_dmg + 2}"
            )

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
