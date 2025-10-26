# app/resources/models/character_dto.py
from dataclasses import dataclass
from typing import Literal

Gender = Literal["male", "female", "other"]

@dataclass(frozen=True, slots=True)
class CharacterCreateDTO:
    """
    DTO для 'входа' (создание).
    (Этот DTO не меняется, он и так был правильным)
    """
    user_id: int
    name: str
    gender: Gender

@dataclass(frozen=True, slots=True)
class CharacterReadDTO:
    """
    DTO для 'выхода' (чтение).
    Теперь он отражает нашу 'чистую' таблицу без статов.
    """
    character_id: int
    user_id: int
    name: str
    gender: Gender
    created_at: str
    updated_at: str