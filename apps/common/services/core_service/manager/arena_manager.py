import json
from typing import Any

from apps.common.services.core_service.redis_key import RedisKeys as Rk
from apps.common.services.core_service.redis_service import RedisService


class ArenaManager:
    """
    Менеджер для управления очередями и заявками на арену в Redis.

    Предоставляет методы для создания, получения, удаления заявок,
    а также для добавления, удаления и поиска игроков в очередях арены.
    """

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    async def create_request(self, char_id: int, meta: dict[str, Any], ttl: int = 300) -> None:
        """
        Создает запись о заявке персонажа на арену с указанным TTL.

        Args:
            char_id: Уникальный идентификатор персонажа, подающего заявку.
            meta: Словарь с метаданными заявки (например, время старта, GameState).
            ttl: Время жизни записи в секундах. По умолчанию 300 секунд (5 минут).
        """
        key = Rk.get_arena_request_key(char_id)
        await self.redis_service.set_value(key, json.dumps(meta), ttl=ttl)

    async def get_request(self, char_id: int) -> dict[str, Any] | None:
        """
        Получает метаданные заявки персонажа на арену.

        Args:
            char_id: Уникальный идентификатор персонажа.

        Returns:
            Словарь с метаданными заявки, если найдена и успешно десериализована, иначе None.

        Raises:
            json.JSONDecodeError: Если сохраненные данные не являются валидным JSON.
        """
        key = Rk.get_arena_request_key(char_id)
        raw = await self.redis_service.get_value(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None

    async def delete_request(self, char_id: int) -> None:
        """
        Удаляет заявку персонажа на арену.

        Args:
            char_id: Уникальный идентификатор персонажа.
        """
        key = Rk.get_arena_request_key(char_id)
        await self.redis_service.delete_key(key)

    async def add_to_queue(self, mode: str, char_id: int, score: float) -> None:
        """
        Добавляет персонажа в очередь арены с указанным режимом и очками (score).

        Args:
            mode: Режим арены (например, "1v1", "group").
            char_id: Уникальный идентификатор персонажа.
            score: Очки персонажа (например, его GameScore) для сортировки в ZSET.
        """
        key = Rk.get_arena_queue_key(mode)
        await self.redis_service.add_to_zset(key, {str(char_id): score})

    async def remove_from_queue(self, mode: str, char_id: int) -> bool:
        """
        Удаляет персонажа из очереди арены.

        Args:
            mode: Режим арены.
            char_id: Уникальный идентификатор персонажа.

        Returns:
            True, если персонаж был успешно удален из очереди, иначе False.
        """
        key = Rk.get_arena_queue_key(mode)
        return await self.redis_service.remove_from_zset(key, str(char_id))

    async def get_candidates(self, mode: str, min_score: float, max_score: float) -> list[str]:
        """
        Ищет кандидатов в очереди арены, чьи очки находятся в заданном диапазоне.

        Args:
            mode: Режим арены.
            min_score: Минимальное значение очков для поиска (включительно).
            max_score: Максимальное значение очков для поиска (включительно).

        Returns:
            Список строковых идентификаторов персонажей, соответствующих критериям.
        """
        key = Rk.get_arena_queue_key(mode)
        return await self.redis_service.get_zset_range_by_score(key, min_score, max_score)

    async def get_score(self, mode: str, char_id: int) -> float | None:
        """
        Получает очки (score) персонажа в указанной очереди арены.

        Args:
            mode: Режим арены.
            char_id: Уникальный идентификатор персонажа.

        Returns:
            Очки персонажа в виде float, если найден, иначе None.
        """
        key = Rk.get_arena_queue_key(mode)
        return await self.redis_service.get_zset_score(key, str(char_id))
