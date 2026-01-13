"""
DTO, описывающие Сессию (Session) и Инициализацию.
"""

from typing import Any, NamedTuple

from pydantic import BaseModel, Field

from apps.game_core.modules.combat.dto.combat_actor_dto import ActorSnapshot


class CombatTeamDTO(BaseModel):
    """Описание команды для создания боя."""

    players: list[int] = Field(default_factory=list)
    pets: list[int] = Field(default_factory=list)
    monsters: list[str] = Field(default_factory=list)


class CombatInitContextDTO(BaseModel):
    """Контекст инициализации (передается в CombatInitService)."""

    mode: str = "standard"
    teams: list[CombatTeamDTO]


class SessionDataDTO(NamedTuple):
    """DTO for transferring assembled data to the persistence method."""

    meta: dict[str, Any]
    actors: dict[str, dict[str, Any]]  # final_id -> {key: value} (HASH/JSON fields)
    targets: dict[str, list[str]]  # final_id -> [enemy_id, ...]


class BattleMeta(BaseModel):
    """Глобальные счетчики (из Redis :meta)"""

    active: int
    step_counter: int
    active_actors_count: int
    teams: dict[str, list[int]]
    winner: str | None = None
    actors_info: dict[str, str] = Field(default_factory=dict)
    dead_actors: list[int] = Field(default_factory=list)
    last_activity_at: int = 0
    battle_type: str
    location_id: str


class BattleContext(BaseModel):
    """
    Глобальный контекст сессии в памяти Воркера.
    """

    session_id: str
    meta: BattleMeta
    actors: dict[int, ActorSnapshot]

    moves_cache: dict[int, dict[str, Any]] = Field(default_factory=dict)
    targets: dict[int, list[int]] = Field(default_factory=dict)
    pending_logs: list[dict] = Field(default_factory=list)

    def get_actor(self, char_id: int) -> ActorSnapshot | None:
        return self.actors.get(char_id)

    def get_enemies(self, char_id: int) -> list[ActorSnapshot]:
        me = self.get_actor(char_id)
        if not me:
            return []
        return [a for a in self.actors.values() if a.team != me.meta.team and a.is_alive]


class MechanicsFlagsDTO(BaseModel):
    """
    Мутация стейта.
    Этот блок управляет тем, как MechanicsService будет записывать результат в Redis.
    """

    pay_cost: bool = True  # Списывать ли энергию/хп за действие
    grant_xp: bool = True  # Начислять ли опыт в буфер
    check_death: bool = True  # Проверять ли смерть после удара
    apply_damage: bool = True  # Наносить ли урон в HP/Shield
    apply_sustain: bool = True  # Считать ли вампиризм/реген
    apply_periodic: bool = False  # Флаг для тиков DoT/HoT
