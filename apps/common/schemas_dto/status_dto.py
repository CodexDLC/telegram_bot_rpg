from pydantic import BaseModel

from apps.common.schemas_dto.character_dto import CharacterReadDTO, CharacterStatsReadDTO
from apps.common.schemas_dto.skill import SkillProgressDTO


class SymbioteReadDTO(BaseModel):
    """DTO для данных Симбиота."""

    symbiote_name: str
    level: int
    experience: int
    # Другие поля симбиота, если есть


class FullCharacterDataDTO(BaseModel):
    """
    Полный пакет данных о персонаже для отображения в меню статуса.
    """

    character: CharacterReadDTO
    stats: CharacterStatsReadDTO
    symbiote: SymbioteReadDTO | None = None
    skills: list[SkillProgressDTO] = []

    # Агрегированные статы (с учетом бонусов)
    total_stats: dict[str, dict] = {}  # {stat_key: {base: X, bonus: Y, total: Z}}
