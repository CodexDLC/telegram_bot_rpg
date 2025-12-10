"""
Модуль содержит DTO (Data Transfer Objects) для работы с навыками персонажа.

Определяет структуры данных для передачи информации о ставках опыта навыков
(`SkillRateDTO`), прогрессе навыков (`SkillProgressDTO`)
и данных для отображения навыков в UI (`SkillDisplayDTO`).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from apps.common.database.model_orm.skill import SkillProgressState


class SkillRateDTO(BaseModel):
    """
    DTO для ставок опыта навыков персонажа (`character_skill_rates`).
    Определяет, насколько эффективно персонаж осваивает конкретный навык.
    """

    character_id: int  # Уникальный идентификатор персонажа.
    skill_key: str  # Ключ навыка (например, "melee_combat", "alchemy").
    xp_per_tick: int  # Количество бонусного XP за "тик" (единицу действия),
    # зависящее от характеристик персонажа.

    model_config = ConfigDict(from_attributes=True)


class SkillProgressDTO(BaseModel):
    """
    DTO для прогресса навыков персонажа (`character_skill_progress`).
    Содержит текущее состояние развития навыка.
    """

    character_id: int  # Уникальный идентификатор персонажа.
    skill_key: str  # Ключ навыка.
    total_xp: int  # Общее количество опыта, накопленного в этом навыке.
    is_unlocked: bool  # Флаг, указывающий, разблокирован ли навык для использования.
    progress_state: SkillProgressState  # Текущее состояние прогресса навыка (например, "PLUS", "PAUSE").
    created_at: datetime  # Дата и время создания записи о прогрессе навыка.
    updated_at: datetime  # Дата и время последнего обновления записи о прогрессе навыка.

    model_config = ConfigDict(from_attributes=True)


class SkillDisplayDTO(BaseModel):
    """
    DTO для отображения информации о навыке в пользовательском интерфейсе.
    Содержит рассчитанные данные, такие как звание, процент прогресса и эффективный максимальный опыт.
    """

    skill_key: str  # Ключ навыка.
    title: str  # Текущее звание персонажа в этом навыке (например, "Новичок", "Мастер").
    percentage: float  # Процент прогресса навыка до следующего уровня/звания.
    total_xp: int  # Общее количество опыта, накопленного в этом навыке.
    effective_max_xp: int  # Эффективное максимальное количество опыта для текущего уровня/звания,
    # учитывающее множители навыка.
