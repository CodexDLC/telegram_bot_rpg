from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import UsersRepoORM
from apps.common.schemas_dto import UserUpsertDTO
from apps.common.services.core_service.redis_key import RedisKeys
from apps.common.services.core_service.redis_service import RedisService


class AuthClient:
    """
    Клиент для работы с пользователями (регистрация, обновление данных, выход).
    """

    def __init__(self, session: AsyncSession, redis_service: RedisService | None = None):
        self.repo = UsersRepoORM(session)
        self.redis_service = redis_service

    async def upsert_user(self, user_dto: UserUpsertDTO) -> None:
        """
        Создает или обновляет пользователя в БД.
        """
        await self.repo.upsert_user(user_dto)

    async def logout(self, user_id: int) -> None:
        """
        Выполняет выход пользователя: очищает сессии в Redis.
        """
        if not self.redis_service:
            return

        # Очищаем сессию лобби
        await self.redis_service.delete_key(RedisKeys.get_lobby_session_key(user_id))

        # Очищаем активную сессию аккаунта (если есть)
        # TODO: Добавить очистку других сессий (бой, инвентарь), если нужно
        # await self.redis_service.delete_key(RedisKeys.get_account_key(char_id))
        # (но мы не знаем char_id здесь, так что пока только юзерские данные)
