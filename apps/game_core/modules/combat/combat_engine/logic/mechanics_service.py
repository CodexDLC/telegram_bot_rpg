from loguru import logger as log

from apps.game_core.modules.combat.dto.combat_pipeline_dto import (
    InteractionResultDTO,
    PipelineContextDTO,
)
from apps.game_core.modules.combat.dto.combat_session_dto import ActorSnapshot


class MechanicsService:
    """
    Сервис применения результатов боя (Commit Phase).
    Отвечает за изменение состояния акторов (HP, Tokens, XP) на основе InteractionResultDTO.
    """

    def apply_interaction_result(
        self,
        ctx: PipelineContextDTO,
        result: InteractionResultDTO,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
    ) -> None:
        """
        Применяет результаты взаимодействия к акторам.
        """
        if not target:
            # Если цели нет (например, селф-бафф), применяем только к источнику
            self._apply_source_changes(source, result)
            return

        # 1. Урон
        if result.damage_final > 0:
            target.meta.hp -= result.damage_final
            log.info(f"Mechanics | {target.char_id} took {result.damage_final} damage. HP: {target.meta.hp}")

        # 2. Токены (Attacker)
        if result.tokens_awarded_attacker:
            for _token in result.tokens_awarded_attacker:
                # TODO: Реализовать маппинг токенов (CRIT_TOKEN -> crit)
                pass

        # 3. Токены (Defender)
        if result.tokens_awarded_defender:
            for _token in result.tokens_awarded_defender:
                pass

        # 4. XP (Buffer)
        # TODO: Запись в XP Buffer

    def _apply_source_changes(self, source: ActorSnapshot, result: InteractionResultDTO) -> None:
        pass
