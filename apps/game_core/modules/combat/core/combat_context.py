# apps/game_core/modules/combat/core/combat_context.py
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CombatActorContext:
    """
    Полный контекст актора в памяти воркера.
    Собирается из разных ключей Redis (State, Cache, Effects).
    """

    char_id: int

    # :state (HASH) - Hot Data
    hp: int = 0
    energy: int = 0
    tactics: int = 0
    afk_level: int = 0
    tokens: dict[str, int] = field(default_factory=dict)

    # :cache (ReJSON) - Calculated Stats
    stats: dict[str, float] = field(default_factory=dict)

    # :effects (ReJSON) - Active Effects
    effects: list[dict[str, Any]] = field(default_factory=list)

    # Meta info (из actors_info)
    role: str = "player"  # player/ai
    team: str = "red"

    def is_dead(self) -> bool:
        return self.hp <= 0


@dataclass
class CombatSessionContext:
    """
    Слепок всей сессии для обработки тика.
    """

    session_id: str
    step_counter: int
    active_actors: int
    meta: dict[str, Any]

    # Словарь всех загруженных актеров {char_id: Context}
    actors: dict[int, CombatActorContext] = field(default_factory=dict)

    # Очереди (загружаются отдельно, если нужно, но обычно передаются в task)
    # logs: List[str] = field(default_factory=list)
