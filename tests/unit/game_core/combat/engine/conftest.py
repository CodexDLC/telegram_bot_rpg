import pytest

from backend.domains.user_features.combat.dto import (
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    ActorStats,
    CombatMoveDTO,
    FeintHandDTO,
    InteractionResultDTO,
    PipelineContextDTO,
    PipelineFlagsDTO,
    PipelineModsDTO,
    PipelinePhasesDTO,
    PipelineStagesDTO,
    TriggerRulesFlagsDTO,
)
from common.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


@pytest.fixture
def basic_actor_stats():
    """
    Базовые статы для тестов.
    """
    mods = CombatModifiersDTO(
        main_hand_accuracy=0.9,
        main_hand_damage_base=100.0,
        main_hand_damage_spread=0.1,
        main_hand_crit_chance=0.2,
        main_hand_penetration=0.0,
        dodge_chance=0.1,
        dodge_cap=0.5,
        anti_dodge_chance=0.0,
        parry_chance=0.1,
        parry_cap=0.5,
        shield_block_chance=0.0,
        shield_block_cap=0.5,
        physical_resistance=0.1,
        damage_reduction_flat=5.0,
        magical_damage_base=50.0,
        magical_crit_chance=0.1,
    )
    skills = CombatSkillsDTO(
        skill_swords=10.0,
        skill_heavy_armor=0.0,
        skill_dual_wield=50.0,  # Для тестов дуалов
    )
    return ActorStats(mods=mods, skills=skills)


@pytest.fixture
def basic_actor_snapshot(basic_actor_stats):
    """
    Снапшот актора.
    """
    meta = ActorMetaDTO(
        id=1,
        name="Hero",
        type="player",
        team="blue",
        hp=100,
        max_hp=100,
        en=50,
        max_en=50,
        tactics=0,
        tokens={"gift": 1, "tactics": 5},
        feints=FeintHandDTO(arsenal=["feint_hit", "feint_crit"]),
    )
    raw = ActorRawDTO()
    return ActorSnapshot(
        meta=meta, raw=raw, stats=basic_actor_stats, loadout=ActorLoadoutDTO(layout={"main_hand": "skill_swords"})
    )


@pytest.fixture
def basic_context():
    """
    Контекст пайплайна.
    """
    return PipelineContextDTO(
        phases=PipelinePhasesDTO(),
        flags=PipelineFlagsDTO(),
        mods=PipelineModsDTO(),
        stages=PipelineStagesDTO(),
        triggers=TriggerRulesFlagsDTO(),
        result=InteractionResultDTO(source_id=1, target_id=2),
    )


@pytest.fixture
def combat_move_attack():
    return CombatMoveDTO(move_id="move_1", char_id=1, strategy="exchange", payload={"target_id": 2})
