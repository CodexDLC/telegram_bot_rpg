"""
Модуль содержит DTO (Data Transfer Objects) для управления боевыми сессиями.

Определяет структуры данных для статистики бойца (`BattleStatsDTO`),
динамического состояния бойца (`FighterStateDTO`), источников
характеристик (`StatSourceData`) и контейнера боевой сессии (`CombatSessionContainerDTO`).
"""

from typing import Any

from pydantic import BaseModel, Field

from apps.common.schemas_dto.item_dto import InventoryItemDTO


class BattleStatsDTO(BaseModel):
    """
    Статистика эффективности бойца за одну боевую сессию.
    Используется для аналитики и отображения результатов боя.
    """

    damage_dealt: int = 0  # Общее количество урона, нанесенного противникам.
    damage_taken: int = 0  # Общее количество урона, полученного от противников.
    healing_done: int = 0  # Общее количество восстановленного HP.
    blocks_success: int = 0  # Количество успешных блоков.
    dodges_success: int = 0  # Количество успешных уворотов.
    crits_landed: int = 0  # Количество нанесенных критических ударов.
    kills: int = 0  # Количество убитых противников.


class FighterStateDTO(BaseModel):
    """
    Динамическое состояние бойца в текущей боевой сессии.
    Эти данные постоянно обновляются в процессе боя.
    """

    hp_current: int  # Текущее количество HP бойца.
    energy_current: int  # Текущее количество энергии/маны бойца.
    targets: list[int] = Field(default_factory=list)  # Список ID текущих целей бойца (порядок важен).
    switch_charges: int = 0  # Количество доступных "зарядов" для смены цели/тактики.
    max_switch_charges: int = 0  # Максимальное количество зарядов смены тактики.
    exchange_count: int = 0  # Количество раундов (обменов ходами), в которых участвовал боец.
    tokens: dict[str, int] = Field(default_factory=dict)  # Временные токены, накапливаемые в бою (например, "ярость").
    effects: dict[str, Any] = Field(default_factory=dict)  # Активные временные эффекты (баффы/дебаффы).
    stats: BattleStatsDTO = Field(default_factory=BattleStatsDTO)  # Статистика бойца за текущий бой.
    xp_buffer: dict[str, int] = Field(default_factory=dict)  # Буфер накопленного опыта для навыков.
    consumable_used_this_round: bool = False  # Блокировка предмета до размена
    item_cooldowns: dict[int, int] = Field(default_factory=dict)  # {inventory_id: exchange_count_ready}
    afk_penalty_level: int = 0  # Уровень штрафа за бездействие (AFK).


class StatSourceData(BaseModel):
    """
    Представляет данные о значении характеристики из различных источников.
    Используется для агрегации характеристик.
    """

    base: float = 0.0  # Базовое значение характеристики (от персонажа).
    equipment: float = 0.0  # Бонус от экипированных предметов.
    skills: float = 0.0  # Бонус от активных навыков/способностей.
    buffs_flat: dict[str, float] = Field(default_factory=dict)  # Плоские бонусы от баффов/дебаффов.
    buffs_percent: dict[str, float] = Field(default_factory=dict)  # Процентные бонусы от баффов/дебаффов.


class CombatSessionContainerDTO(BaseModel):
    """
    Полный контейнер данных для участника боевой сессии.
    Собирает все необходимые данные для расчетов и логики боя.
    """

    char_id: int  # Идентификатор персонажа.
    team: str  # Команда, к которой принадлежит боец (например, "blue", "red").
    name: str  # Имя бойца.
    is_ai: bool = False  # Флаг, указывающий, является ли боец управляемым AI.
    active_abilities: list[str] = Field(default_factory=list)  # Список ключей активных способностей бойца.
    persistent_pipeline: list[str] = Field(default_factory=list)  # Список ключей пассивных эффектов/способностей.
    equipped_items: list[InventoryItemDTO] = Field(default_factory=list)  # Список экипированных предметов.
    belt_items: list[InventoryItemDTO] = Field(default_factory=list)  # Список предметов в быстрых слотах.
    quick_slot_limit: int = 0  # Максимальное количество быстрых слотов.
    state: FighterStateDTO | None = None  # Динамическое состояние бойца в текущем раунде.
    stats: dict[str, StatSourceData] = Field(default_factory=dict)  # Агрегированные характеристики бойца.
