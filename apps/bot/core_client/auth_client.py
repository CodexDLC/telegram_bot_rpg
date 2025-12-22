from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import UsersRepoORM
from apps.common.schemas_dto import UserUpsertDTO


class AuthClient:
    """
    Клиент для работы с пользователями (регистрация, обновление данных).
    """

    def __init__(self, session: AsyncSession):
        self.repo = UsersRepoORM(session)

    async def upsert_user(self, user_dto: UserUpsertDTO) -> None:
        """
        Создает или обновляет пользователя в БД.
        """
        await self.repo.upsert_user(user_dto)
