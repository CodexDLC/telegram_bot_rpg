# database/repositories/ORM/users_repo_orm.py

import logging
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.user_dto import UserUpsertDTO, UserDTO
from database.db_contract.i_users_repo import IUserRepo

from database.model_orm.user import User

log = logging.getLogger(__name__)

class UsersRepoORM(IUserRepo):

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_user(self, user_data: UserUpsertDTO) -> None:
        """
        Создает или обновляет пользователя, используя 'входную' DTO.
        """
        user_data_dict = user_data.model_dump()

        # noinspection PyArgumentList
        orm_user = User(**user_data_dict)

        await self.session.merge(orm_user)
        log.debug(f"Выполнен Merge для User: {orm_user.telegram_id}")



    async def get_user(self, telegram_id: int, **kwargs) -> Optional[UserDTO]:
        """
        Возвращает 'полную' DTO пользователя из БД.
        """
        stmt = select(User).where(User.telegram_id == telegram_id)

        result = await self.session.execute(stmt)
        orm_user = result.scalar_one_or_none()

        if orm_user:
            return UserDTO.model_validate(orm_user)
        return None



    async def get_users(self, **kwargs) -> List[UserDTO]:
        """
        Возвращает список 'полных' DTO (для админки).
        """
        stmt = select(User)

        result = await self.session.execute(stmt)
        orm_users_list = result.all()

        if orm_users_list:
            return [UserDTO.model_validate(orm_user) for orm_user in orm_users_list]
        return []