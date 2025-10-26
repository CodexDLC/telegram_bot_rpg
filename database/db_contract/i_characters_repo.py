# database/db_contract/i_characters_repo.py

from abc import abstractmethod, ABC

from app.resources.models.character_dto import CharacterReadDTO, CharacterCreateDTO


class ICharactersRepo(ABC):
    @abstractmethod
    async def create_character(self, character_data: CharacterCreateDTO) -> None:
        """
        Создает персонажа.
        """
        pass

    @abstractmethod
    async def get_character(self, character_id: int) -> CharacterReadDTO | None:
        """
        Возвращает персонажа.
        """
        pass
    @abstractmethod


    async def get_characters(self, user_id: int) -> list | None:
        """
        Возвращает список персонажей.
        """
        pass

    @abstractmethod
    async def delete_characters(self,character_id: int):
        """
        Удаляет персонажа.
        """
        pass