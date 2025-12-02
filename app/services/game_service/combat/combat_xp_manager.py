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

        Args:
            actor: DTO актора.
            item_subtype: Подтип предмета/действия (e.g., "sword", "shield").
            outcome: Результат действия ("success", "miss", "crit").
        """
        if not actor.state:
            log.warning(f"RegisterActionXP_Fail | reason=no_actor_state actor_id={actor.char_id}")
            return

        # 1. Определяем навык
        skill_key = XP_SOURCE_MAP.get(item_subtype)
        if not skill_key:
            log.warning(f"RegisterActionXP_Skip | reason=no_skill_mapping subtype={item_subtype}")
            return

        # 2. Определяем множитель
        mult = OUTCOME_MULTIPLIERS.get(outcome, 0.0)
        if mult == 0:
            log.trace(f"RegisterActionXP_Skip | reason=zero_multiplier outcome={outcome}")
            return

        # 3. Считаем очки
        raw_points = int(BASE_ACTION_XP * mult)

        # 4. Пишем в буфер (в памяти)
        current_xp = actor.state.xp_buffer.get(skill_key, 0)
        actor.state.xp_buffer[skill_key] = current_xp + raw_points

        log.trace(
            f"XPBufferUpdate | actor_id={actor.char_id} skill={skill_key} outcome={outcome} points_added={raw_points} new_total={actor.state.xp_buffer[skill_key]}"
        )
