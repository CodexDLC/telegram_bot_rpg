# database/db_contract/i_characters_repo.py

from abc import abstractmethod, ABC

from app.resources.models.character_dto import CharacterReadDTO


class ICharactersRepo(ABC):
    @abstractmethod
    async def create_character(self, character_data: CharacterReadDTO) -> None:
        """
        Создает персонажа.
        """
        pass

    @abstractmethod
    async def get_character(self, user_id: int) -> CharacterReadDTO:
        """
        Возвращает персонажа.
        """
        pass
    @abstractmethod


    async def get_characters(self, user_id: int) -> list:
        """
        Возвращает список персонажей.
        """
        pass