"""
Account API Client.
HTTP клиент для взаимодействия с backend /account/...
"""

from typing import Any

from common.schemas.lobby import LobbyListDTO
from common.schemas.onboarding import OnboardingUIPayloadDTO
from common.schemas.response import CoreResponseDTO
from common.schemas.user import UserDTO
from game_client.telegram_bot.core.api_client import BaseApiClient


class AccountClient(BaseApiClient):
    """
    Единый клиент для Account домена.
    Покрывает: Registration, Lobby, Onboarding, Login.
    """

    # --- Registration ---

    async def register_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
        is_premium: bool = False,
    ) -> CoreResponseDTO[UserDTO]:
        """
        POST /account/register
        Регистрация или обновление пользователя.
        """
        body = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "language_code": language_code,
            "is_premium": is_premium,
        }

        data = await self._request("POST", "/account/register", json=body)
        return CoreResponseDTO[UserDTO](**data)

    # --- Lobby ---

    async def initialize_lobby(self, user_id: int) -> CoreResponseDTO[LobbyListDTO | OnboardingUIPayloadDTO]:
        """
        POST /account/lobby/{user_id}/initialize
        Вход в лобби. Автоматически создает первого персонажа если нет.
        Возвращает либо список персонажей, либо онбординг.
        """
        data = await self._request("POST", f"/account/lobby/{user_id}/initialize")
        return CoreResponseDTO(**data)

    async def get_characters(self, user_id: int) -> CoreResponseDTO[LobbyListDTO]:
        """
        GET /account/lobby/{user_id}/characters
        Получить список персонажей пользователя.
        """
        data = await self._request("GET", f"/account/lobby/{user_id}/characters")
        return CoreResponseDTO[LobbyListDTO](**data)

    async def create_character(self, user_id: int) -> CoreResponseDTO[OnboardingUIPayloadDTO]:
        """
        POST /account/lobby/{user_id}/characters
        Создать нового персонажа (запускает онбординг).
        """
        data = await self._request("POST", f"/account/lobby/{user_id}/characters")
        return CoreResponseDTO[OnboardingUIPayloadDTO](**data)

    async def delete_character(self, char_id: int, user_id: int) -> CoreResponseDTO[LobbyListDTO]:
        """
        DELETE /account/lobby/characters/{char_id}?user_id={user_id}
        Удалить персонажа.
        """
        data = await self._request("DELETE", f"/account/lobby/characters/{char_id}", params={"user_id": user_id})
        return CoreResponseDTO[LobbyListDTO](**data)

    # --- Onboarding ---

    async def onboarding_action(
        self, char_id: int, action: str, value: Any = None
    ) -> CoreResponseDTO[OnboardingUIPayloadDTO]:
        """
        POST /account/onboarding/{char_id}/action
        Отправить действие онбординга (set_name, set_gender, finalize).
        """
        body = {"action": action, "value": value}

        data = await self._request("POST", f"/account/onboarding/{char_id}/action", json=body)
        return CoreResponseDTO[OnboardingUIPayloadDTO](**data)

    # --- Login ---

    async def login(self, user_id: int, char_id: int) -> CoreResponseDTO:
        """
        POST /account/login/{user_id}/characters/{char_id}/login
        Войти в игру выбранным персонажем.
        Возвращает состояние персонажа (COMBAT, SCENARIO, EXPLORATION).
        """
        data = await self._request("POST", f"/account/login/{user_id}/characters/{char_id}/login")
        return CoreResponseDTO(**data)
