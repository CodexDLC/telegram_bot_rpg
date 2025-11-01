# app/resources/schemas_dto/skill.py
from pydantic import BaseModel, ConfigDict
from database.model_orm.skill import SkillProgressState  # Убедись, что этот импорт будет работать


class SkillRateDTO(BaseModel):
    """
    DTO для 'character_skill_rates' (БСО)
    (Содержит все поля из ORM для чтения)
    """
    character_id: int
    skill_key: str
    xp_per_tick: int

    model_config = ConfigDict(from_attributes=True)


class SkillProgressDTO(BaseModel):
    """
    DTO для 'character_skill_progress'
    (Содержит все хранимые поля из ORM)
    """
    character_id: int
    skill_key: str
    total_xp: int

    progress_state: SkillProgressState

    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class SkillDisplayDTO(BaseModel):
    """
    DTO, которую Хэндлер получает для отображения игроку.
    Содержит "рассчитанные" данные.
    """
    skill_key: str
    title: str
    percentage: float
    total_xp: int
    effective_max_xp: int
