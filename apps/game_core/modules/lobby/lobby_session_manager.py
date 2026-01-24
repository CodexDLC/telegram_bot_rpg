import contextlib
import json

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.postgres.repositories import get_character_repo
from apps.common.schemas_dto import CharacterReadDTO, CharacterShellCreateDTO
from backend.database.redis.redis_key import RedisKeys
from backend.database.redis import RedisService


class LobbySessionManager:
    """
    Менеджер данных лобби.
    Инкапсулирует работу с БД (через Repository) и Кэшем (через RedisService).
    """

    def __init__(self, session: AsyncSession, redis_service: RedisService):
        # Менеджер сам создает нужный ему репозиторий
        self.char_repo = get_character_repo(session)
        self.redis_service = redis_service

    async def get_characters(self, user_id: int) -> list[CharacterReadDTO]:
        """
        Получает список персонажей (Cache-Aside паттерн).
        1. Ищет в Redis.
        2. Если нет - ищет в БД и сохраняет в Redis.
        """
        cache_key = RedisKeys.get_lobby_session_key(user_id)

        # 1. Попытка чтения из кэша
        cached_data = await self.redis_service.get_value(cache_key)
        if cached_data:
            with contextlib.suppress(Exception):
                chars_data = json.loads(cached_data)
                return [CharacterReadDTO(**char) for char in chars_data]

        # 2. Чтение из БД
        characters = await self.char_repo.get_characters(user_id)

        if not characters:
            return []

        # 3. Запись в кэш (TTL 1 час)
        with contextlib.suppress(Exception):
            chars_json = json.dumps([char.model_dump(mode="json") for char in characters])
            await self.redis_service.set_value(cache_key, chars_json, ttl=3600)

        return characters

    async def create_character(self, user_id: int) -> int:
        """
        Создает персонажа в БД и инвалидирует кэш лобби.
        """
        dto = CharacterShellCreateDTO(user_id=user_id)
        char_id = await self.char_repo.create_character_shell(dto)

        # Инвалидация кэша
        await self._invalidate_cache(user_id)
        return char_id

    async def delete_character(self, user_id: int, char_id: int) -> bool:
        """
        Удаляет персонажа из БД и инвалидирует кэш лобби.
        """
        with contextlib.suppress(Exception):
            await self.char_repo.delete_characters(char_id)
            await self._invalidate_cache(user_id)
            return True
        return False

    async def _invalidate_cache(self, user_id: int) -> None:
        """
        Сбрасывает кэш сессии лобби.
        """
        cache_key = RedisKeys.get_lobby_session_key(user_id)
        await self.redis_service.delete_key(cache_key)
