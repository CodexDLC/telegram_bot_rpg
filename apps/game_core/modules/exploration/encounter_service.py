# apps/game_core/modules/exploration/encounter_service.py
import random
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.model_orm.monster import GeneratedClanORM
from apps.common.schemas_dto.exploration_dto import DetectionStatus, EncounterDTO, EncounterType
from apps.game_core.system.factories.monster.encounter_pool_service import EncounterPoolService


class EncounterService:
    """
    Сервис, отвечающий за логику случайных встреч.
    """

    TIER_CHANCES = {0: 0.05, 1: 0.15, 2: 0.25, 3: 0.40, 4: 0.55, 5: 0.70, 6: 0.85, 7: 1.0}

    def __init__(self, session: AsyncSession):
        self.session = session
        self.pool_service = EncounterPoolService(session)

    async def calculate_encounter(
        self, char_id: int, nav_data: dict[str, Any], target_loc_id: str
    ) -> EncounterDTO | None:
        flags = nav_data.get("flags", {})
        if flags.get("is_safe_zone"):
            return None

        tier = int(flags.get("threat_tier", 0))
        survival_lvl = 1

        enc_type = self._try_spawn_encounter(tier, survival_lvl)
        if not enc_type:
            return None

        log.info(f"EncounterService | Encounter spawned for {char_id}. Type: {enc_type}")

        if enc_type == EncounterType.COMBAT:
            biome_id = nav_data.get("terrain", "forest")
            raw_tags = nav_data.get("tags", [])

            clan = await self.pool_service.get_random_encounter(tier, biome_id, raw_tags)

            if not clan:
                log.warning(f"EncounterService | No mob found for tier={tier}, biome={biome_id}")
                return None
            return self._create_combat_encounter(survival_lvl, tier, target_loc_id, clan)
        else:
            return self._create_narrative_encounter()

    def _try_spawn_encounter(self, tier: int, survival_skill: int) -> EncounterType | None:
        base_chance = self.TIER_CHANCES.get(tier, 0.1)
        final_chance = max(0.02, base_chance - (survival_skill * 0.01))
        if random.random() > final_chance:
            return None
        return EncounterType.COMBAT if random.random() < 0.7 else EncounterType.NARRATIVE

    def _check_detection(self, survival_skill: int, mob_tier: int) -> DetectionStatus:
        luck = random.randint(-1, 1)
        if (survival_skill - mob_tier + luck) >= 0:
            return DetectionStatus.DETECTED
        return DetectionStatus.AMBUSH

    def _create_combat_encounter(
        self, survival_lvl: int, tier: int, target_loc_id: str, clan: GeneratedClanORM
    ) -> EncounterDTO:
        status = self._check_detection(survival_lvl, tier)

        flavor: dict[str, Any] = clan.flavor_content or {}  # type: ignore
        name = clan.name_ru or clan.family_id  # type: ignore

        # --- ИЗМЕНЕНО: Выбираем описание в зависимости от статуса ---
        if status == DetectionStatus.DETECTED:
            # Если игрок заметил, показываем внешний вид или поведение
            description = flavor.get("appearance", flavor.get("behavior", f"Вы замечаете группу: {name}."))
        else:  # AMBUSH
            # Если засада, показываем описание нападения
            description = flavor.get("encounter", f"{name} нападает на вас из засады!")

        return EncounterDTO(
            type=EncounterType.COMBAT,
            encounter_id=str(clan.id),
            name=name,  # type: ignore
            description=description,
            status=status,
            mob_tier=tier,
            metadata={"target_loc": target_loc_id},
        )

    def _create_narrative_encounter(self) -> EncounterDTO:
        return EncounterDTO(
            type=EncounterType.NARRATIVE,
            encounter_id="chest_wood_01",
            name="Старый сундук",
            description="Вы нашли старый сундук в густой траве.",
        )
