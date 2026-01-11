"""
Внутренние DTO боевого модуля (Domain Layer).
Используются только внутри воркеров, менеджеров и сервисов.
Не должны импортироваться в Common или Client слоях.
"""

from typing import Any

from pydantic import BaseModel, Field

from apps.common.schemas_dto.combat_source_dto import CombatMoveDTO

# Импортируем кирпичики из Common
from apps.common.schemas_dto.modifier_dto import (
    CombatSkillsDTO,
    DefensiveStatsDTO,
    ElementalStatsDTO,
    EnvironmentalStatsDTO,
    MagicalStatsDTO,
    MainHandStatsDTO,
    MitigationStatsDTO,
    OffHandStatsDTO,
    PhysicalStatsDTO,
    SpecialStatsDTO,
    StatusStatsDTO,
    VitalsDTO,
)

# ==============================================================================
# 1. ORCHESTRATION (Manager -> Worker)
# ==============================================================================


class CombatActionDTO(BaseModel):
    """
    Задача для Воркера в очереди `q:actions`.
    Содержит полные данные мува (Cut & Paste).
    """

    action_type: str  # "item", "instant", "exchange", "forced"

    # Основной мув (Инициатор)
    move: CombatMoveDTO

    # Ответный мув (для exchange)
    partner_move: CombatMoveDTO | None = None

    is_forced: bool = False


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


# ==============================================================================
# 3. WORKER RUNTIME (Context)
# ==============================================================================


class ActorState(BaseModel):
    """
    Изменяемые параметры из Redis Hash `:state`.
    Hot Data.
    """

    hp: int = 0
    max_hp: int = 0
    en: int = 0
    max_en: int = 0
    initiative: int = 0
    energy: int = 0
    tactics: int = 0
    afk_level: int = 0
    is_dead: bool = False
    exchange_count: int = 0
    tokens: dict[str, int] = Field(default_factory=dict)  # {"gift": 1, "parry": 1}


class ActorRawDTO(BaseModel):
    """
    Строгая типизация для `:raw` данных.
    Cold Data.
    """

    name: str = "Unknown"
    stats: dict[str, Any] = Field(default_factory=dict)  # TODO: Use ActorStats
    attributes: dict[str, Any] = Field(default_factory=dict)
    modifiers: dict[str, Any] = Field(default_factory=dict)

    # Whitelist доступных абилок
    known_abilities: list[str] = Field(default_factory=list)

    # Маппинг экипировки для XP сервиса
    # {"main_hand": "light_weapons", "head_armor": "heavy_armor"}
    equipment_layout: dict[str, str] = Field(default_factory=dict)


class ActiveAbilityDTO(BaseModel):
    """
    Активные эффекты из Redis JSON `:active_abilities`.
    Dynamic Modifiers.
    """

    uid: str
    ability_id: str
    source_id: int
    expire_at_exchange: int  # Таймер жизни (в разменах)
    impact: dict[str, int] = Field(default_factory=dict)  # {"hp": -10}
    payload: dict[str, Any] = Field(default_factory=dict)


class ActorStats(
    VitalsDTO,
    MainHandStatsDTO,
    OffHandStatsDTO,
    PhysicalStatsDTO,
    MagicalStatsDTO,
    DefensiveStatsDTO,
    MitigationStatsDTO,
    ElementalStatsDTO,
    SpecialStatsDTO,
    EnvironmentalStatsDTO,
):
    """
    Готовые статы для математики (In-Memory Calculated).
    Гибридная структура:
    - Основные боевые статы: Плоские (наследуются).
    - Скиллы и Статусы: Вложенные (для удобства передачи в подсистемы).
    """

    calculated_at: float = 0.0

    # Вложенные блоки
    skills: CombatSkillsDTO = Field(default_factory=CombatSkillsDTO)
    status: StatusStatsDTO = Field(default_factory=StatusStatsDTO)

    @classmethod
    def from_flat_dict(cls, flat_data: dict[str, Any]) -> "ActorStats":
        """
        Фабрика для создания ActorStats из плоского словаря (результат WaterfallCalculator).
        Автоматически распределяет поля по вложенным DTO.
        """
        # 1. Выкусываем данные для вложенных DTO
        skills_data = {}
        status_data = {}
        main_data = flat_data.copy()  # Копия, чтобы не портить исходник (хотя можно и портить)

        # Список полей для Skills и Status (можно оптимизировать через model_fields)
        skills_fields = CombatSkillsDTO.model_fields.keys()
        status_fields = StatusStatsDTO.model_fields.keys()

        for key in list(main_data.keys()):
            if key in skills_fields:
                skills_data[key] = main_data.pop(key)
            elif key in status_fields:
                status_data[key] = main_data.pop(key)

        # 2. Создаем вложенные объекты
        skills_obj = CombatSkillsDTO(**skills_data)
        status_obj = StatusStatsDTO(**status_data)

        # 3. Создаем основной объект (Pydantic сам возьмет нужные поля из main_data)
        # Важно: main_data теперь не содержит skills/status полей, чтобы не было конфликтов,
        # хотя Pydantic extra='ignore' (по умолчанию) или 'forbid' (в CombatModifiersDTO)
        # В CombatModifiersDTO стоит 'forbid', но ActorStats наследует кирпичики, у которых default config.
        # Лучше передать явно.

        return cls(**main_data, skills=skills_obj, status=status_obj)


class ActorSnapshot(BaseModel):
    """
    Агрегатор данных актера в памяти.
    The Root Object.
    """

    char_id: int
    team: str

    state: ActorState

    # Calculated (In-Memory only)
    # Может быть None, если еще не посчитан в этом цикле
    stats: ActorStats | None = None

    # Optimization: Dirty Flags
    # Список полей, которые изменились в :raw и требуют пересчета
    dirty_stats: set[str] = Field(default_factory=set)

    active_abilities: list[ActiveAbilityDTO] = Field(default_factory=list)
    raw: ActorRawDTO  # Typed Source
    xp_buffer: dict[str, int] = Field(default_factory=dict)  # Accumulator

    @property
    def is_alive(self) -> bool:
        return not self.state.is_dead and self.state.hp > 0


class BattleMeta(BaseModel):
    """Глобальные счетчики (из Redis :meta)"""

    active: int
    step_counter: int
    active_actors_count: int
    teams: dict[str, list[int]]
    winner: str | None = None  # Имя победившей команды (blue/red)
    actors_info: dict[str, str] = Field(default_factory=dict)  # {id: type}
    dead_actors: list[int] = Field(default_factory=list)  # Список мертвых
    last_activity_at: int = 0  # Timestamp последней активности
    battle_type: str
    location_id: str


class BattleContext(BaseModel):
    """
    Глобальный контекст сессии в памяти Воркера.
    """

    session_id: str
    meta: BattleMeta
    actors: dict[int, ActorSnapshot]

    # Moves Cache (Загруженные JSON-документы мувов для резолвинга Pointers)
    moves_cache: dict[int, dict[str, Any]] = Field(default_factory=dict)

    # Targets Cache (Очереди целей)
    targets: dict[int, list[int]] = Field(default_factory=dict)

    # Output Buffers
    pending_logs: list[dict] = Field(default_factory=list)

    def get_actor(self, char_id: int) -> ActorSnapshot | None:
        return self.actors.get(char_id)

    def get_enemies(self, char_id: int) -> list[ActorSnapshot]:
        me = self.get_actor(char_id)
        if not me:
            return []
        return [a for a in self.actors.values() if a.team != me.team and a.is_alive]
