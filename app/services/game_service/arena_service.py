# app/services/game_service/arena_service.py
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.core_service.manager.account_manager import account_manager
from app.services.game_service.combat.combat_service import CombatService
from app.services.game_service.stats_aggregation_service import (
    StatInfo,
    StatsAggregationService,
)
from database.repositories import get_character_repo

DUMMY_CHAR_ID = -1


class ArenaService:
    def __init__(self, session: AsyncSession, char_id: int):
        self.session = session
        self.char_id = char_id

    async def start_training_dummy(self) -> str | None:
        char_repo = get_character_repo(self.session)
        char_dto = await char_repo.get_character(self.char_id)
        char_name = char_dto.name if char_dto else "Герой"

        aggregator = StatsAggregationService(self.session)
        total_stats = await aggregator.get_character_total_stats(self.char_id)

        mods = total_stats.get("modifiers", {})
        hp_max_data: dict[str, Any] | StatInfo = mods.get("hp_max", {})
        energy_max_data: dict[str, Any] | StatInfo = mods.get("energy_max", {})

        player_hp = 100
        if isinstance(hp_max_data, dict):
            player_hp = int(hp_max_data.get("total", 100))
        elif isinstance(hp_max_data, StatInfo):
            player_hp = int(hp_max_data.total)

        player_en = 100
        if isinstance(energy_max_data, dict):
            player_en = int(energy_max_data.get("total", 100))
        elif isinstance(energy_max_data, StatInfo):
            player_en = int(energy_max_data.total)

        log.info(f"Создаем Тень с HP={player_hp} и EN={player_en}")

        dummy_id = DUMMY_CHAR_ID

        session_id = await CombatService.create_battle([], is_pve=True)
        combat_service = CombatService(session_id)

        await combat_service.add_participant(self.session, self.char_id, team="blue", name=char_name, is_ai=False)

        await combat_service.add_dummy_participant(
            char_id=dummy_id,
            hp=player_hp,
            energy=player_en,
            name="👥 Тень",
        )

        await account_manager.update_account_fields(self.char_id, {"state": "combat", "combat_session_id": session_id})

        return session_id
