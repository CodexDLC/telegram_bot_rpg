from typing import Any

from pydantic import BaseModel, Field


class CombatInteractionContext(BaseModel):
    """
    Задача на исполнение (Task).
    Генерируется Менеджером, читается Исполнителем.
    """

    session_id: str
    step_index: int  # Порядковый номер внутри батча
    source_id: int
    target_id: int | None = None
    skill_id: str | None = None
    interaction_type: str = "exchange"  # "exchange", "instant"
    payload: dict[str, Any] = Field(default_factory=dict)


class ActorState(BaseModel):
    """Изменяемые параметры (Hot Data из Redis HASH)"""

    hp: int
    max_hp: int
    en: int
    max_en: int
    tactics: int = 0
    afk_level: int = 0
    is_dead: bool = False


class ActorStats(BaseModel):
    """Готовые статы для математики (из Redis JSON :cache)"""

    # Атака
    dmg_min: int = 0
    dmg_max: int = 0
    crit_chance: float = 0.0
    crit_power: float = 1.5
    hit_rate: float = 1.0
    penetration: float = 0.0

    # Защита
    armor: int = 0
    evasion: float = 0.0
    magic_resist: float = 0.0
    block_chance: float = 0.0
    block_power: float = 0.5  # % снижения урона при блоке
    thorns_damage: int = 0

    # Ресурсы
    vampirism: float = 0.0
    regeneration: int = 0


class ActorEffect(BaseModel):
    """Активный эффект (из Redis JSON :effects)"""

    uid: str
    effect_id: str
    source_id: int
    expires_at_step: int
    payload: dict[str, Any] = Field(default_factory=dict)


class ActorSnapshot(BaseModel):
    """
    Единый объект бойца в памяти Воркера.
    """

    char_id: int
    team: str  # "red" / "blue"
    state: ActorState
    stats: ActorStats
    effects: list[ActorEffect] = Field(default_factory=list)

    @property
    def is_alive(self) -> bool:
        return not self.state.is_dead and self.state.hp > 0


class BattleMeta(BaseModel):
    """Глобальные счетчики (из Redis :meta)"""

    active: int
    step_counter: int
    active_actors_count: int
    teams: dict[str, list[int]]
    battle_type: str
    location_id: str


class BattleContext(BaseModel):
    """
    Главный объект, который передается во все сервисы.
    Содержит ВСЮ информацию о текущем состоянии боя.
    """

    session_id: str
    meta: BattleMeta
    actors: dict[int, ActorSnapshot]
    pending_logs: list[dict] = Field(default_factory=list)

    def get_actor(self, char_id: int) -> ActorSnapshot | None:
        return self.actors.get(char_id)

    def get_enemies(self, char_id: int) -> list[ActorSnapshot]:
        me = self.get_actor(char_id)
        if not me:
            return []
        return [a for a in self.actors.values() if a.team != me.team and a.is_alive]


class InteractionResultDTO(BaseModel):
    """Результат расчета CombatCalculator (Output DTO)"""

    damage_final: int = 0
    shield_dmg: int = 0
    lifesteal_amount: int = 0
    thorns_damage: int = 0

    is_crit: bool = False
    is_blocked: bool = False
    is_dodged: bool = False
    is_miss: bool = False
    is_counter: bool = False

    tokens_atk: dict[str, int] = Field(default_factory=dict)
    tokens_def: dict[str, int] = Field(default_factory=dict)

    logs: list[str] = Field(default_factory=list)
    visual_bar: str = ""
