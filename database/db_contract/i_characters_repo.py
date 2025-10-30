# database/db_contract/i_characters_repo.py

from abc import abstractmethod, ABC
from typing import Dict, Optional

from app.resources.models.character_dto import (
    CharacterReadDTO, CharacterCreateDTO,
    CharacterStatsReadDTO, CharacterStatsUpdateDTO
)


class ICharactersRepo(ABC):
    @abstractmethod
    async def create_character(self, character_data: CharacterCreateDTO) -> int:
        """
        Создает персонажа.
        """
        pass

    @abstractmethod
    async def get_character(self, character_id: int, **kwargs) -> CharacterReadDTO | None:
        """
        Возвращает персонажа.
        """
        pass

    @abstractmethod


    async def get_characters(self, user_id: int, **kwargs) -> list | None:
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

class ICharacterStatsRepo(ABC):

    @abstractmethod
    async def get_stats(self, character_id: int, **kwargs) -> CharacterStatsReadDTO | None:
        """
        Возвращает персонажа.
        """
        pass

    @abstractmethod
    async def update_stats(self,character_id: int, stats_data: CharacterStatsUpdateDTO):
        """
        Обновляет персонажа.
        """
        pass

    @abstractmethod
    async def add_stats(self, character_id: int, stats_to_add: Dict[str, int]) -> Optional[CharacterStatsReadDTO]:
        """
        Атомарно добавляет значения к существующим статам И
        ВОЗВРАЩАЕТ обновленные данные.
        """
        pass