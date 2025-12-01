# app/services/core_service/redis_service.py
import json
from typing import Any

from loguru import logger as log
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.redis_client import redis_client


class RedisService:
    """
    Сервис для взаимодействия с Redis, предоставляющий удобные методы
    для работы с различными структурами данных (хеши, множества).
    """

    def __init__(self, client: Redis):
        self.redis_client = client
        log.debug(f"Инициализирован {self.__class__.__name__} с клиентом: {client}")

    async def set_hash_json(self, key: str, field: str, data: dict[str, Any]) -> None:
        """Сериализует словарь в JSON и сохраняет его в поле хеша."""
        try:
            data_json = json.dumps(data)
            await self.redis_client.hset(key, field, data_json)  # type: ignore
            log.debug(f"Установлено значение для key='{key}', field='{field}'.")
        except TypeError as e:
            log.error(f"Ошибка сериализации JSON для key='{key}', field='{field}': {e}")
        except RedisError as e:
            log.exception(f"Ошибка Redis при выполнении hset для key='{key}': {e}")

    async def set_hash_fields(self, key: str, data: dict[str, Any]) -> None:
        """Устанавливает НЕСКОЛЬКО полей в хеше за один вызов."""
        try:
            await self.redis_client.hset(key, mapping=data)  # type: ignore
            log.debug(f"Установлены поля {list(data.keys())} для key='{key}'.")
        except RedisError as e:
            log.exception(f"Ошибка Redis при выполнении hset (mapping) для key='{key}': {e}")

    async def get_hash_json(self, key: str, field: str) -> dict[str, Any] | None:
        """Получает JSON-строку из поля хеша и десериализует ее в словарь."""
        try:
            data_json = await self.redis_client.hget(key, field)  # type: ignore
            if data_json:
                # data_json уже str, json.loads отлично это переварит
                log.debug(f"Найдено значение для key='{key}', field='{field}'.")
                return json.loads(data_json)
            log.debug(f"Значение для key='{key}', field='{field}' не найдено.")
            return None
        except json.JSONDecodeError as e:
            log.error(f"Ошибка десериализации JSON для key='{key}', field='{field}': {e}")
            return None
        except RedisError as e:
            log.exception(f"Ошибка Redis при выполнении hget для key='{key}': {e}")
            return None

    async def get_hash_field(self, key: str, field: str) -> str | None:
        """Получает одно поле из хеша."""
        try:
            value = await self.redis_client.hget(key, field)  # type: ignore
            if value:
                log.debug(f"Получено значение для key='{key}', field='{field}'.")
                return value
            log.debug(f"Значение для key='{key}', field='{field}' не найдено.")
            return None
        except RedisError as e:
            log.exception(f"Ошибка Redis при выполнении hget для key='{key}': {e}")
            return None

    async def get_all_hash(self, key: str) -> dict[str, Any] | None:
        """Получает все поля и значения из хеша."""
        try:
            data_dict = await self.redis_client.hgetall(key)  # type: ignore
            if data_dict:
                log.debug(f"Получены все поля для key='{key}'.")
                return data_dict
            log.debug(f"Хеш по ключу '{key}' не найден или пуст.")
            return None
        except RedisError as e:
            log.exception(f"Ошибка Redis при выполнении hgetall для key='{key}': {e}")
            return None

    async def delete_hash_json(self, key: str) -> None:
        """Удаляет весь хеш по ключу."""
        try:
            await self.redis_client.delete(key)  # type: ignore
            log.debug(f"Хеш по ключу '{key}' удален.")
        except RedisError as e:
            log.exception(f"Ошибка Redis при удалении key='{key}': {e}")

    async def delete_hash_field(self, key: str, field: str) -> None:
        """Удаляет одно поле из хеша."""
        try:
            await self.redis_client.hdel(key, field)  # type: ignore
            log.debug(f"Поле '{field}' удалено из хеша '{key}'.")
        except RedisError as e:
            log.exception(f"Ошибка Redis при удалении поля '{field}' из key='{key}': {e}")

    async def add_to_set(self, key: str, value: str | int) -> None:
        """Добавляет значение в множество."""
        try:
            await self.redis_client.sadd(key, str(value))  # type: ignore
            log.debug(f"Значение '{value}' добавлено в множество '{key}'.")
        except RedisError as e:
            log.exception(f"Ошибка Redis при добавлении в множество '{key}': {e}")

    async def get_to_set(self, key: str) -> set[str]:
        """Возвращает все элементы множества."""
        try:
            members = await self.redis_client.smembers(key)  # type: ignore
            log.debug(f"Получено {len(members)} элементов из множества '{key}'.")
            return members
        except RedisError as e:
            log.exception(f"Ошибка Redis при получении множества '{key}': {e}")
            return set()

    async def is_set_member(self, key: str, value: str | int) -> bool:
        """Проверяет, является ли значение элементом множества."""
        try:
            is_member = await self.redis_client.sismember(key, str(value))  # type: ignore
            log.debug(f"Проверка принадлежности '{value}' к множеству '{key}': {is_member}.")
            return bool(is_member)
        except RedisError as e:
            log.exception(f"Ошибка Redis при проверке множества '{key}': {e}")
            return False

    async def remove_from_set(self, key: str, value: str | int) -> None:
        """Удаляет значение из множества."""
        try:
            await self.redis_client.srem(key, str(value))  # type: ignore
            log.debug(f"Значение '{value}' удалено из множества '{key}'.")
        except RedisError as e:
            log.exception(f"Ошибка Redis при удалении из множества '{key}': {e}")

    async def key_exists(self, key: str) -> bool:
        """Проверяет существование ключа."""
        try:
            exists = await self.redis_client.exists(key)  # type: ignore
            log.debug(f"Проверка существования ключа '{key}': {exists}.")
            return bool(exists)
        except RedisError as e:
            log.exception(f"Ошибка Redis при проверке ключа '{key}': {e}")
            return False

    # --- SORTED SETS (ZSET) ---

    async def add_to_zset(self, key: str, mapping: dict[str, float]) -> int:
        """
        Добавляет элементы в Sorted Set.
        :param mapping: Словарь {member: score}
        :return: Количество добавленных элементов.
        """
        try:
            # redis-py ожидает mapping={member: score}
            count = await self.redis_client.zadd(key, mapping)  # type: ignore
            log.debug(f"В ZSET '{key}' добавлено/обновлено {count} элементов.")
            return int(count)
        except RedisError as e:
            log.exception(f"Ошибка Redis zadd для '{key}': {e}")
            return 0

    async def get_zset_score(self, key: str, member: str) -> float | None:
        """Возвращает Score участника."""
        try:
            score = await self.redis_client.zscore(key, member)  # type: ignore
            return float(score) if score is not None else None
        except RedisError as e:
            log.exception(f"Ошибка Redis zscore для '{key}': {e}")
            return None

    async def get_zset_range_by_score(self, key: str, min_score: float, max_score: float) -> list[str]:
        """Возвращает список members в диапазоне очков."""
        try:
            # Возвращает список строк (members)
            res = await self.redis_client.zrangebyscore(key, min_score, max_score)  # type: ignore
            return res
        except RedisError as e:
            log.exception(f"Ошибка Redis zrangebyscore для '{key}': {e}")
            return []

    async def remove_from_zset(self, key: str, member: str) -> bool:
        """Удаляет элемент из ZSET."""
        try:
            count = await self.redis_client.zrem(key, member)  # type: ignore
            if count > 0:
                log.debug(f"Элемент '{member}' удален из ZSET '{key}'.")
                return True
            return False
        except RedisError as e:
            log.exception(f"Ошибка Redis zrem для '{key}': {e}")
            return False

    # --- BASIC K/V (String) ---

    async def set_value(self, key: str, value: str, ttl: int | None = None) -> None:
        """
        Устанавливает значение ключа (String).
        :param ttl: Время жизни в секундах (опционально).
        """
        try:
            # ex=ttl работает только если ttl передано
            await self.redis_client.set(key, value, ex=ttl)  # type: ignore
            log.debug(f"Установлен ключ '{key}' (TTL={ttl}).")
        except RedisError as e:
            log.exception(f"Ошибка Redis set для '{key}': {e}")

    async def get_value(self, key: str) -> str | None:
        """Получает значение ключа (String)."""
        try:
            val = await self.redis_client.get(key)  # type: ignore
            return str(val) if val is not None else None
        except RedisError as e:
            log.exception(f"Ошибка Redis get для '{key}': {e}")
            return None

    async def delete_key(self, key: str) -> None:
        """Универсальное удаление ключа."""
        try:
            await self.redis_client.delete(key)  # type: ignore
            log.debug(f"Ключ '{key}' удален.")
        except RedisError as e:
            log.exception(f"Ошибка Redis delete для '{key}': {e}")


# Глобальный экземпляр сервиса
redis_service = RedisService(client=redis_client)
