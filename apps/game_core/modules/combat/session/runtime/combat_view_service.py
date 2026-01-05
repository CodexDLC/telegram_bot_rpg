# apps/game_core/modules/combat/session/runtime/combat_view_service.py
"""
Файл: app/game_core/modules/combat/session/combat_view_service.py
"""

import json
import math

from loguru import logger as log

from apps.common.schemas_dto.combat_source_dto import (
    ActorSnapshotDTO,
    CombatDashboardDTO,
    CombatLogDTO,
)
from apps.game_core.modules.combat.combat_redis_fields import CombatSessionFields as Csf
from apps.game_core.modules.combat.core.combat_stats_calculator import StatsCalculator


class CombatViewService:
    """
    Read Model (Pure Mapper).
    Преобразует сырые данные (dict, list) в DTO.
    Не имеет зависимостей от Redis/Manager.
    """

    def build_dashboard_dto(
        self,
        session_id: str,
        char_id: int,
        meta: dict[str, str],
        actors_data: dict[str, str],
        queue_list: list[str],
    ) -> CombatDashboardDTO:
        """
        Собирает CombatDashboardDTO из сырых данных.
        """
        # 1. Определяем статус
        is_active = int(meta.get(Csf.ACTIVE, 0)) == 1
        winner = meta.get(Csf.WINNER)

        status = "active"
        if not is_active or winner:
            status = "finished"
        elif len(queue_list) == 0:
            status = "waiting"

        # 2. Парсим акторов
        player_dto = None
        allies = []
        enemies = []
        belt_items = []

        # Сначала ищем себя
        my_raw = actors_data.get(str(char_id))
        if not my_raw:
            # Если игрока нет в сессии (ошибка данных), возвращаем пустой DTO или кидаем ошибку
            # Лучше кинуть, чтобы SessionService обработал
            raise ValueError(f"Player {char_id} not found in session actors")

        my_data = json.loads(my_raw)
        my_team = my_data.get("team")

        # Извлекаем поясную сумку
        raw_belt = my_data.get("belt_items", [])
        belt_items = raw_belt  # Уже dict

        # Извлекаем switch_charges из state
        switch_charges = 0
        if "state" in my_data and "switch_charges" in my_data["state"]:
            switch_charges = my_data["state"]["switch_charges"]

        for aid_str, raw in actors_data.items():
            data = json.loads(raw)
            dto = self._map_actor(data)

            aid = int(aid_str)
            if aid == char_id:
                player_dto = dto
            elif data.get("team") == my_team:
                allies.append(dto)
            else:
                enemies.append(dto)

        # 3. Награды
        rewards = {}
        if meta.get(Csf.REWARDS):
            try:
                all_rewards = json.loads(meta[Csf.REWARDS])
                rewards = all_rewards.get(str(char_id), {})
            except json.JSONDecodeError:
                log.warning(f"Failed to parse rewards for session {session_id}")

        # 4. Текущая цель
        current_target = None
        if queue_list:
            target_id = int(queue_list[0])
            for e in enemies:
                if e.char_id == target_id:
                    current_target = e
                    break

        # Ensure player_dto is not None before passing to CombatDashboardDTO
        if player_dto is None:
            raise ValueError(f"Player {char_id} DTO could not be created")

        return CombatDashboardDTO(
            session_id=session_id,
            status=status,
            queue_count=len(queue_list),
            player=player_dto,
            current_target=current_target,
            allies=allies,
            enemies=enemies,
            winner_team=winner,
            rewards=rewards,
            belt_items=belt_items,
            switch_charges=switch_charges,
        )

    def build_logs_dto(self, raw_logs: list[str], page: int = 0) -> CombatLogDTO:
        """
        Собирает CombatLogDTO из списка сырых логов.
        """
        page_size = 5
        total = len(raw_logs)
        total_pages = math.ceil(total / page_size)
        if total_pages == 0:
            total_pages = 1

        end_idx = total - (page * page_size)
        start_idx = max(0, end_idx - page_size)

        chunk = []
        if end_idx > 0:
            chunk = raw_logs[start_idx:end_idx]

        return CombatLogDTO(logs=chunk, page=page, total_pages=total_pages)

    def _map_actor(self, data: dict) -> ActorSnapshotDTO:
        """Собирает DTO одного актера с расчетом Max HP."""
        state = data.get("state", {})
        stats = data.get("stats", {})

        final_stats = StatsCalculator.aggregate_all(stats)

        # Определение Layout оружия
        layout = "1h"
        equipped = data.get("equipped_items", [])
        has_offhand = False
        for item in equipped:
            if item.get("slot") == "off_hand" and item.get("item_type") == "weapon":
                has_offhand = True
                break
        if has_offhand:
            layout = "dual"

        return ActorSnapshotDTO(
            char_id=data["char_id"],
            name=data.get("name", ""),
            team=data.get("team", ""),
            is_dead=state.get("hp_current", 0) <= 0,
            hp_current=int(state.get("hp_current", 0)),
            hp_max=int(final_stats.get("hp_max", 100)),
            energy_current=int(state.get("energy_current", 0)),
            energy_max=int(final_stats.get("energy_max", 100)),
            effects=list(state.get("effects", {}).keys()),
            tokens=state.get("tokens", {}),
            weapon_layout=layout,
        )
