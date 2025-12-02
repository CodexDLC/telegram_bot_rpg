# app/services/game_service/combat/combat_xp_manager.py
from loguru import logger as log

from app.resources.game_data.xp_rules import BASE_ACTION_XP, OUTCOME_MULTIPLIERS, XP_SOURCE_MAP
from app.resources.schemas_dto.combat_source_dto import CombatSessionContainerDTO


class CombatXPManager:
    """
    Отвечает ТОЛЬКО за расчет и накопление опыта в бою.
    Помогает разгрузить CombatService (God Object).
    """

    @staticmethod
    def register_action(actor: CombatSessionContainerDTO, item_subtype: str, outcome: str) -> None:
        """
        Рассчитывает опыт и пишет его в xp_buffer актора.
        Не делает запросов к БД.
        """
        if not actor.state:
            return

        # 1. Определяем навык
        skill_key = XP_SOURCE_MAP.get(item_subtype)
        if not skill_key:
            return

            # 2. Определяем множитель
        mult = OUTCOME_MULTIPLIERS.get(outcome, 0.0)
        if mult == 0:
            return

        # 3. Считаем очки
        raw_points = int(BASE_ACTION_XP * mult)

        # 4. Пишем в буфер (в памяти)
        current = actor.state.xp_buffer.get(skill_key, 0)
        actor.state.xp_buffer[skill_key] = current + raw_points

        log.trace(f"XP Buffer [{actor.name}]: +{raw_points} to {skill_key} ({outcome})")
