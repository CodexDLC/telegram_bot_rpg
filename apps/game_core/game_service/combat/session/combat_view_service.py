import json
import time
from typing import Any

from apps.common.schemas_dto import CombatSessionContainerDTO, StatSourceData
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.game_core.game_service.combat.core.combat_stats_calculator import StatsCalculator


class CombatViewService:
    """
    Сервис-фасад для подготовки данных о состоянии боя для отображения в UI.
    Собирает данные из различных источников и представляет их в виде,
    удобном для рендеринга.
    """

    def __init__(self, combat_manager: CombatManager, account_manager: AccountManager):
        self.combat_manager = combat_manager
        self.account_manager = account_manager

    async def get_dashboard_data(self, session_id: str, char_id: int) -> dict[str, Any]:
        """
        Собирает все необходимые данные для отрисовки дашборда.
        """
        all_actors_json = await self.combat_manager.get_rbc_all_actors_json(session_id)

        player_dto, enemies_data, allies_data, my_team = None, [], [], "blue"
        all_actors = []

        if all_actors_json:
            for pid_str, raw in all_actors_json.items():
                pid = int(pid_str)
                dto = CombatSessionContainerDTO.model_validate_json(raw)
                all_actors.append(dto)
                if pid == char_id:
                    player_dto = dto
                    my_team = dto.team

        for actor in all_actors:
            hp_max = 100
            if actor.stats:
                hp_base = actor.stats.get("hp_max", StatSourceData(base=100))
                hp_max = int(StatsCalculator.calculate("hp_max", hp_base))

            info = {
                "char_id": actor.char_id,
                "name": actor.name,
                "hp_current": actor.state.hp_current if actor.state else 0,
                "hp_max": hp_max,
                "is_ready": False,
            }
            if actor.char_id == char_id:
                continue
            elif actor.team == my_team:
                allies_data.append(info)
            else:
                enemies_data.append(info)

        player_state_dict = {}
        if player_dto and player_dto.state:
            hp_max = int(StatsCalculator.calculate("hp_max", player_dto.stats.get("hp_max", StatSourceData(base=100))))
            en_max = int(
                StatsCalculator.calculate("energy_max", player_dto.stats.get("energy_max", StatSourceData(base=100)))
            )
            player_state_dict = {
                "hp_current": player_dto.state.hp_current,
                "hp_max": hp_max,
                "energy_current": player_dto.state.energy_current,
                "energy_max": en_max,
                "tokens": player_dto.state.tokens,
                "switch_charges": player_dto.state.switch_charges,
            }

        target_id = await self.combat_manager.get_rbc_next_target_id(session_id, char_id)

        is_spectator = not player_dto or not player_dto.state or player_dto.state.hp_current <= 0

        return {
            "player_state": player_state_dict,
            "target_id": target_id,
            "enemies_list": enemies_data,
            "allies_list": allies_data,
            "is_spectator": is_spectator,
        }

    async def get_menu_data(self, session_id: str, char_id: int, menu_type: str) -> dict[str, Any]:
        """
        Возвращает данные для меню умений или предметов.
        """
        raw = await self.combat_manager.get_rbc_actor_state_json(session_id, char_id)
        if not raw:
            return {}

        actor = CombatSessionContainerDTO.model_validate_json(raw)

        if menu_type == "skills":
            return {
                "actor_name": actor.name,
                "active_skills": actor.active_abilities or [],
            }
        elif menu_type == "items":
            return {
                "belt_items": [item.model_dump() for item in actor.belt_items],
                "quick_slot_limit": actor.quick_slot_limit,
            }
        return {}

    async def get_logs_data(self, session_id: str) -> list[dict]:
        """
        Возвращает полный список логов боя.
        Пагинация происходит на стороне UI-сервиса.
        """
        all_logs_json = await self.combat_manager.get_combat_log_list(session_id)
        return [json.loads(log_json) for log_json in all_logs_json]

    async def get_results_data(self, session_id: str, char_id: int) -> dict[str, Any]:
        """Возвращает данные для экрана результатов."""
        meta = await self.combat_manager.get_session_meta(session_id)
        if not meta:
            return {}

        raw = await self.combat_manager.get_rbc_actor_state_json(session_id, char_id)
        actor = CombatSessionContainerDTO.model_validate_json(raw) if raw else None

        return {
            "winner": meta.get("winner", "none"),
            "start_time": int(meta.get("start_time", 0)),
            "end_time": int(meta.get("end_time", time.time())),
            "player_name": actor.name if actor else "Игрок",
            "player_team": actor.team if actor else "none",
        }
