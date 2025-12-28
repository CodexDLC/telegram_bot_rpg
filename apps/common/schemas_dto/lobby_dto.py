from pydantic import BaseModel

from apps.common.schemas_dto.character_dto import CharacterReadDTO


class LobbyInitDTO(BaseModel):
    """
    DTO для инициализации лобби.
    Содержит список персонажей пользователя.
    """

    characters: list[CharacterReadDTO]
