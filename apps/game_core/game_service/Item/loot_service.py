import random

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto import InventoryItemDTO
from apps.game_core.game_service.Item.item_distribution_service import ItemDistributionService

# Базовые константы (в будущем могут переехать в конфиг монстра)
BASE_DROP_CHANCE = 0.3
SKINNING_FAIL_CHANCE = 0.2


class LootService:
    """
    Сервис Правил Лута (Game Rules Layer).

    Отвечает за ПРИНЯТИЕ РЕШЕНИЙ:
    1. Расчет RNG (повезло/не повезло).
    2. Определение качества лута (Тир, Редкость).
    3. Логика профессий (Свежевание).

    Делегирует физическое создание предмета сервису ItemDistributionService.
    """

    def __init__(self, session: AsyncSession):
        self.distribution_service = ItemDistributionService(session)

    async def roll_combat_loot(self, mob_tier: int, luck_modifier: float = 1.0) -> InventoryItemDTO | None:
        """
        Рассчитывает лут после убийства монстра.

        Args:
            mob_tier: Уровень/Тир монстра.
            luck_modifier: Множитель удачи (1.0 = норма, 1.2 = +20% шанс).

        Returns:
            InventoryItemDTO (готовый к выдаче, лежит у Системы) или None.
        """
        # 1. Ролл на факт выпадения
        # Если luck_modifier = 1.5, то шанс становится 0.45
        final_chance = min(1.0, BASE_DROP_CHANCE * luck_modifier)
        roll = random.random()

        if roll > final_chance:
            log.debug(f"LootService | Drop failed: roll={roll:.2f} > chance={final_chance:.2f}")
            return None

        # 2. Определение Тира предмета
        # Логика:
        # 15% - Хлам (Тир - 1)
        # 80% - Норма (Тир моба)
        # 5%  - Джекпот (Тир + 1), тоже скейлится от удачи

        tier_roll = random.random()
        jackpot_chance = 0.05 * luck_modifier

        if tier_roll < 0.15:
            item_tier = max(0, mob_tier - 1)
        elif tier_roll > (1.0 - jackpot_chance):
            item_tier = mob_tier + 1
        else:
            item_tier = mob_tier

        # 3. Делегирование создания (Distribution Layer)
        # Мы не знаем, меч это или броня - пусть решает рандом внутри дистрибьютора
        loot_item = await self.distribution_service.prepare_random_loot(tier=item_tier)

        if loot_item:
            log.info(f"LootService | Loot generated: {loot_item.data.name} (Tier {item_tier})")

        return loot_item

    async def process_skinning(
        self, loot_table: dict[str, dict], player_skill_level: int, tool_quality: float = 1.0
    ) -> list[InventoryItemDTO]:
        """
        Обрабатывает попытку "Освежевать" (Skinning).

        Args:
            loot_table: Таблица лута моба {"res_wolf_pelt": {"min_skill": 1, "tier": 1}}.
            player_skill_level: Уровень навыка игрока.
            tool_quality: Качество ножа (влияет на шанс успеха).
        """
        rewards = []

        for resource_id, rules in loot_table.items():
            min_skill = rules.get("min_skill", 0)
            base_tier = rules.get("tier", 1)

            # Шанс успеха зависит от скилла и инструмента
            # Если скилл равен требуемому -> шанс успеха 80% (при базовом 20% фейла)
            # Каждый уровень скилла сверху добавляет 5%
            skill_delta = player_skill_level - min_skill
            success_chance = (1.0 - SKINNING_FAIL_CHANCE) + (skill_delta * 0.05)
            success_chance = min(1.0, success_chance * tool_quality)

            # Если провал - даем мусор ("Рваная шкура")
            if random.random() > success_chance:
                resource_id = "res_torn_pelt"
                target_tier = 0
            else:
                target_tier = base_tier

            # Генерируем ресурс
            resource_item = await self.distribution_service.prepare_specific_item(base_id=resource_id, tier=target_tier)

            if resource_item:
                rewards.append(resource_item)

        return rewards
