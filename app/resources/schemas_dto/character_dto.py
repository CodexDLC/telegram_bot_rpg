# app/resources/schemas_dto/character_dto.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Gender = Literal["male", "female", "other"]


class CharacterShellCreateDTO(BaseModel):
    """
    DTO для 'входа' (создание "оболочки" персонажа).
    Содержит ТОЛЬКО ID пользователя.
    """

    user_id: int


class CharacterOnboardingUpdateDTO(BaseModel):
    """
    DTO для 'входа' (обновление персонажа после онбординга).
    """

    name: str
    gender: Gender  # (Gender у вас уже определен)
    game_stage: str


class CharacterReadDTO(BaseModel):
    """
    DTO для выхода

    """

    character_id: int
    user_id: int
    name: str
    gender: Gender
    game_stage: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CharacterStatsUpdateDTO(BaseModel):
    """
    DTO для обновления данных.
    """

    strength: int
    agility: int
    endurance: int

    intelligence: int
    wisdom: int
    men: int

    perception: int
    charisma: int
    luck: int


class CharacterStatsReadDTO(CharacterStatsUpdateDTO):
    """
    DTO для получения данных

    """

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
