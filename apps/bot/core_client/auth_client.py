from typing import TYPE_CHECKING

from apps.common.database.repositories import UsersRepoORM
from apps.common.schemas_dto import UserUpsertDTO
from apps.common.services.core_service.redis_key import RedisKeys

if TYPE_CHECKING:
    from apps.game_core.core_container import CoreContainer


class AuthClient:
    """
    Клиент для работы с пользователями (регистрация, обновление данных, выход).
    """

    def __init__(self, core_container: "CoreContainer"):
        self.core = core_container

    async def upsert_user(self, user_dto: UserUpsertDTO) -> None:
        """
        Создает или обновляет пользователя в БД.
        """
        async with self.core.get_session_context() as session:
            repo = UsersRepoORM(session)
            await repo.upsert_user(user_dto)

    async def logout(self, user_id: int) -> None:
        """
        Выполняет выход пользователя: очищает сессии в Redis.
        """
        # Очищаем сессию лобби
        await self.core.redis_service.delete_key(RedisKeys.get_lobby_session_key(user_id))

        # Очищаем активную сессию аккаунта (если есть)
        # TODO: Добавить очистку других сессий (бой, инвентарь), если нужно
        # await self.redis_service.delete_key(RedisKeys.get_account_key(char_id))
        # (но мы не знаем char_id здесь, так что пока только юзерские данные)
