# app/resources/schemas_dto/character_dto.py

from typing import Literal

from pydantic import BaseModel, ConfigDict

Gender = Literal["male", "female", "other"]


class CharacterCreateDTO(BaseModel):
    """
    DTO для 'входа' (создание).
    """
    user_id: int
    name: str
    gender: Gender
    game_stage: str



class CharacterReadDTO(CharacterCreateDTO):
    """
    DTO для выхода

    """

    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)



class CharacterStatsUpdateDTO(BaseModel):
    """
    DTO для обновления данных.
    """
    strength: int
    agility: int
    endurance: int
    charisma: int
    intelligence: int
    perception: int
    luck: int



class CharacterStatsReadDTO(CharacterStatsUpdateDTO):
    """
    DTO для получения данных

    """

    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)