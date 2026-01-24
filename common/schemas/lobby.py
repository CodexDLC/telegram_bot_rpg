from pydantic import BaseModel

from common.schemas.character import CharacterReadDTO


class LobbyListDTO(BaseModel):
    """
    DTO для списка персонажей в лобби.
    """

    characters: list[CharacterReadDTO]
