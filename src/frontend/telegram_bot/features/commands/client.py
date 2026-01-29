from apps.common.schemas_dto.user_dto import UserUpsertDTO

from src.frontend.telegram_bot.core.api_client import BaseApiClient


class AuthClient(BaseApiClient):
    """
    Клиент для работы с пользователями (регистрация, обновление данных, выход).
    """

    async def upsert_user(self, user_dto: UserUpsertDTO) -> None:
        """
        Создает или обновляет пользователя через API.
        POST /auth/login
        """
        await self._request("POST", "/auth/login", json=user_dto.model_dump())

    async def logout(self, user_id: int) -> None:
        """
        Выполняет выход пользователя.
        POST /auth/logout
        """
        await self._request("POST", "/auth/logout", json={"user_id": user_id})
