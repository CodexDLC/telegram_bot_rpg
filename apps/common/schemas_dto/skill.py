"""
Модуль содержит DTO (Data Transfer Objects) для работы с навыками персонажа.

Определяет структуры данных для передачи информации о прогрессе навыков
(`SkillProgressDTO`) и данных для отображения навыков в UI (`SkillDisplayDTO`).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.database.postgres.models.skill import SkillProgressState


class SkillProgressDTO(BaseModel):
    """
    DTO для прогресса навыков персонажа (`character_skill_progress`).
    Содержит текущее состояние развития навыка.
    """

    character_id: int  # Уникальный идентификатор персонажа.
    skill_key: str  # Ключ навыка.
    total_xp: float  # Общее количество опыта (0.0 ... 1.0 ...).
    is_unlocked: bool  # Флаг, указывающий, разблокирован ли навык для использования.
    progress_state: SkillProgressState  # Текущее состояние прогресса навыка (например, "PLUS", "PAUSE").
    created_at: datetime  # Дата и время создания записи о прогрессе навыка.
    updated_at: datetime  # Дата и время последнего обновления записи о прогрессе навыка.

    model_config = ConfigDict(from_attributes=True)


class SkillDisplayDTO(BaseModel):
    """
    DTO для отображения информации о навыке в пользовательском интерфейсе.
    Упрощенная версия: только ключ, название и текущий опыт (который и есть процент/прогресс).
    """

    skill_key: str  # Ключ навыка.
    title: str  # Название навыка (локализованное).
    total_xp: float  # Текущий опыт (Float). Для UI это и есть значение прогресса (например, 0.55 = 55%).
