# app/resources/models/character_dto.py
from dataclasses import dataclass
from typing import Literal

Gender = Literal["male", "female", "other"]

@dataclass(frozen=True, slots=True)
class CharacterCreateDTO:
    """
    DTO для 'входа' (создание).
    """
    user_id: int
    name: str
    gender: Gender

@dataclass(frozen=True, slots=True)
class CharacterReadDTO:
    """
    DTO для выхода

    """
    character_id: int
    user_id: int
    name: str
    gender: Gender
    created_at: str
    updated_at: str

@dataclass(frozen=True, slots=True)
class CharacterStatsUpdateDTO:
    """
    DTO для обновления данных.
    """
    strength: int
    dexterity: int
    endurance: int
    charisma: int
    intelligence: int
    perception: int
    luck: int


@dataclass(frozen=True, slots=True)
class CharacterStatsReadDTO:
    """
    DTO для получения данных

    """
    character_id: int
    strength: int
    dexterity: int
    endurance: int
    charisma: int
    intelligence: int
    perception: int
    luck: int
    created_at: str
    updated_at: str