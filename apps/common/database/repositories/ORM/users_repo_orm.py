from typing import Any

from loguru import logger as log
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.common.database.db_contract.i_users_repo import IUserRepo
from apps.common.database.model_orm.user import User
from apps.common.schemas_dto.user_dto import UserDTO, UserUpsertDTO


class UsersRepoORM(IUserRepo):
    """
    ORM-реализация репозитория для управления пользователями.

    Этот класс использует SQLAlchemy ORM для взаимодействия с базой данных,
    предоставляя методы для создания, обновления и получения данных пользователей.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует репозиторий с сессией SQLAlchemy.

        Args:
            session: Экземпляр асинхронной сессии.
        """
        self.session = session
        log.debug(f"UsersRepoORM | status=initialized session={session}")

    async def upsert_user(self, user_data: UserUpsertDTO) -> None:
        """
        Создает нового пользователя или обновляет данные существующего с помощью ORM.

        Использует `session.merge()`, который автоматически определяет,
        нужно ли выполнить INSERT или UPDATE на основе первичного ключа.

        Args:
            user_data: DTO с данными для создания или обновления пользователя.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        user_data_dict = user_data.model_dump()
        orm_user = User(**user_data_dict)
        log.debug(f"UsersRepoORM | action=upsert_user telegram_id={orm_user.telegram_id}")

        try:
            await self.session.merge(orm_user)
            log.info(f"UsersRepoORM | action=upsert_user status=success telegram_id={orm_user.telegram_id}")
        except SQLAlchemyError:
            log.exception(f"UsersRepoORM | action=upsert_user status=failed telegram_id={orm_user.telegram_id}")
            raise

    async def get_user(self, telegram_id: int) -> UserDTO | None:
        """
        Находит и возвращает одного пользователя по его `telegram_id` с помощью ORM.

        Args:
            telegram_id: Уникальный идентификатор пользователя в Telegram.

        Returns:
            DTO `UserDTO` пользователя, если найден, иначе None.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        log.debug(f"UsersRepoORM | action=get_user telegram_id={telegram_id}")
        stmt = select(User).where(User.telegram_id == telegram_id)

        try:
            result = await self.session.execute(stmt)
            orm_user: User | None = result.scalar_one_or_none()

            if orm_user:
                log.debug(f"UsersRepoORM | action=get_user status=found telegram_id={telegram_id}")
                return UserDTO.model_validate(orm_user)
            else:
                log.debug(f"UsersRepoORM | action=get_user status=not_found telegram_id={telegram_id}")
                return None
        except SQLAlchemyError:
            log.exception(f"UsersRepoORM | action=get_user status=failed telegram_id={telegram_id}")
            raise

    async def get_users(self) -> list[UserDTO]:
        """
        Возвращает список всех пользователей с помощью ORM.

        Returns:
            Список DTO `UserDTO` всех пользователей.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        log.debug("UsersRepoORM | action=get_users")
        stmt = select(User)

        try:
            result = await self.session.execute(stmt)
            orm_users_list = result.scalars().all()

            if orm_users_list:
                log.debug(f"UsersRepoORM | action=get_users status=found count={len(orm_users_list)}")
                return [UserDTO.model_validate(orm_user) for orm_user in orm_users_list]
            else:
                log.debug("UsersRepoORM | action=get_users status=not_found")
                return []
        except SQLAlchemyError:
            log.exception("UsersRepoORM | action=get_users status=failed")
            raise

    async def get_users_with_pagination(self, offset: int, limit: int) -> tuple[list[Any], int]:
        """
        Возвращает страницу пользователей и общее их количество.
        """
        log.debug(f"UsersRepoORM | action=get_users_with_pagination offset={offset} limit={limit}")
        try:
            count_stmt = select(func.count(User.telegram_id))
            total_res = await self.session.execute(count_stmt)
            total = total_res.scalar_one()

            stmt = (
                select(User)
                .options(selectinload(User.characters))
                .order_by(User.telegram_id)
                .offset(offset)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            orm_users_list = result.scalars().all()

            log.debug(
                f"UsersRepoORM | action=get_users_with_pagination status=success count={len(orm_users_list)} total={total}"
            )
            return list(orm_users_list), total
        except SQLAlchemyError:
            log.exception("UsersRepoORM | action=get_users_with_pagination status=failed")
            raise
