# database/db_contract/i_users_repo.py
from abc import abstractmethod, ABC
from typing import Optional, List

from app.resources.models.user_dto import UserUpsertDTO, UserDTO


# Импортируем обе модели



class IUserRepo(ABC):

    @abstractmethod
    async def upsert_user(self, user_data: UserUpsertDTO) -> None:
        """
        Создает или обновляет пользователя, используя 'входную' DTO.
        """
        pass

    @abstractmethod
    async def get_user(self, telegram_id: int) -> Optional[UserDTO]:
        """
        Возвращает 'полную' DTO пользователя из БД.
        """
        pass

    @abstractmethod
    async def get_users(self) -> List[UserDTO]:
        """
        Возвращает список 'полных' DTO (для админки).
        """
        pass