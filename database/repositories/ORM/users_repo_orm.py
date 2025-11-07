# database/repositories/ORM/users_repo_orm.py
import logging
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.resources.schemas_dto.user_dto import UserUpsertDTO, UserDTO
from database.db_contract.i_users_repo import IUserRepo
from database.model_orm.user import User

log = logging.getLogger(__name__)


class UsersRepoORM(IUserRepo):
    """
    ORM-реализация репозитория для управления пользователями.

    Этот класс использует SQLAlchemy ORM для взаимодействия с базой данных.

    Attributes:
        session (AsyncSession): Асинхронная сессия SQLAlchemy.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует репозиторий с сессией SQLAlchemy.

        Args:
            session (AsyncSession): Экземпляр асинхронной сессии.
        """
        self.session = session
        log.debug(f"Инициализирован {self.__class__.__name__} с сессией: {session}")

    async def upsert_user(self, user_data: UserUpsertDTO) -> None:
        """
        Создает нового пользователя или обновляет существующего с помощью ORM.

        Использует `session.merge()`, который автоматически определяет,
        нужно ли выполнить INSERT или UPDATE на основе первичного ключа.

        Args:
            user_data (UserUpsertDTO): DTO с данными для создания/обновления.

        Returns:
            None

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        user_data_dict = user_data.model_dump()
        # noinspection PyArgumentList
        orm_user = User(**user_data_dict)
        log.debug(f"Выполнение 'merge' для User с telegram_id={orm_user.telegram_id}")

        try:
            await self.session.merge(orm_user)
            log.debug(f"Пользователь с telegram_id={orm_user.telegram_id} был успешно создан или обновлен.")
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при выполнении 'upsert_user' для telegram_id={orm_user.telegram_id}: {e}")
            raise

    async def get_user(self, telegram_id: int, **kwargs) -> Optional[UserDTO]:
        """
        Находит и возвращает одного пользователя по `telegram_id` с помощью ORM.

        Args:
            telegram_id (int): Уникальный идентификатор пользователя в Telegram.
            **kwargs: Дополнительные параметры (не используются).

        Returns:
            Optional[UserDTO]: DTO пользователя, если найден, иначе None.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        log.debug(f"Запрос на получение пользователя по telegram_id={telegram_id}")
        stmt = select(User).where(User.telegram_id == telegram_id)

        try:
            result = await self.session.execute(stmt)
            orm_user: Optional[User] = result.scalar_one_or_none()

            if orm_user:
                log.debug(f"Пользователь с telegram_id={telegram_id} найден.")
                return UserDTO.model_validate(orm_user)
            else:
                log.debug(f"Пользователь с telegram_id={telegram_id} не найден.")
                return None
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при выполнении 'get_user' для telegram_id={telegram_id}: {e}")
            raise

    async def get_users(self, **kwargs) -> List[UserDTO]:
        """
        Возвращает список всех пользователей с помощью ORM.

        Args:
            **kwargs: Дополнительные параметры (не используются).

        Returns:
            List[UserDTO]: Список DTO всех пользователей.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        log.debug("Запрос на получение списка всех пользователей.")
        stmt = select(User)

        try:
            result = await self.session.execute(stmt)
            # .scalars() извлекает первый столбец (в данном случае, объекты User)
            orm_users_list = result.scalars().all()

            if orm_users_list:
                log.debug(f"Найдено {len(orm_users_list)} пользователей.")
                return [UserDTO.from_orm(orm_user) for orm_user in orm_users_list]
            else:
                log.debug("Пользователи в базе данных не найдены.")
                return []
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при выполнении 'get_users': {e}")
            raise
