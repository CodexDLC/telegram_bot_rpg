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
        """
        Инициализирует сервис с асинхронным клиентом Redis.

        Args:
            client (Redis): Экземпляр асинхронного клиента Redis.
        """
        self.redis_client = client
        log.debug(f"Инициализирован {self.__class__.__name__} с клиентом: {client}")

    async def set_hash_json(self, key: str, field: str, data: dict[str, Any]) -> None:
        """
        Сериализует словарь в JSON и сохраняет его в поле хеша.

        Args:
            key (str): Ключ хеша в Redis.
            field (str): Поле внутри хеша.
            data (dict): Словарь для сохранения.
        """
        try:
            data_json = json.dumps(data)
            await self.redis_client.hset(key, field, data_json)  # type: ignore
            log.debug(f"Установлено значение для key='{key}', field='{field}'.")
        except TypeError as e:
            log.error(f"Ошибка сериализации JSON для key='{key}', field='{field}': {e}")
        except RedisError as e:
            log.exception(f"Ошибка Redis при выполнении hset для key='{key}': {e}")

    async def set_hash_fields(self, key: str, data: dict[str, Any]) -> None:
        """
        Устанавливает НЕСКОЛЬКО полей в хеше за один вызов.
        Идеально для обновления 'state' и 'location_id' ОДНОВРЕМЕННО.
        """
        try:
            # hset может принимать mapping (словарь)
            await self.redis_client.hset(key, mapping=data)  # type: ignore
            log.debug(f"Установлены поля {list(data.keys())} для key='{key}'.")
        except RedisError as e:
            log.exception(f"Ошибка Redis при выполнении hset (mapping) для key='{key}': {e}")

    async def get_hash_json(self, key: str, field: str) -> dict[str, Any] | None:
        """
        Получает JSON-строку из поля хеша и десериализует ее в словарь.

        Args:
            key (str): Ключ хеша.
            field (str): Поле внутри хеша.

        Returns:
            dict | None: Десериализованный словарь, если данные существуют, иначе None.
        """
        try:
            data_json = await self.redis_client.hget(key, field)  # type: ignore
            if data_json:
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
        """
        Получает одно поле из хеша.
        ...
        """

        try:
            value = await self.redis_client.hget(key, field)  # type: ignore
            if value:
                log.debug(f"Получено значение для key='{key}', field='{field}'.")
                return value.decode("utf-8")
            log.debug(f"Значение для key='{key}', field='{field}' не найдено.")
            return None
        except RedisError as e:
            log.exception(f"Ошибка Redis при выполнении hget для key='{key}': {e}")
            return None

    async def get_all_hash(self, key: str) -> dict[str, Any] | None:
        """
        Получает все поля и значения из хеша.
        ...
        """
        try:
            data_dict = await self.redis_client.hgetall(key)  # type: ignore
            if data_dict:
                log.debug(f"Получены все поля для key='{key}'.")
                return {k.decode("utf-8"): v.decode("utf-8") for k, v in data_dict.items()}
            log.debug(f"Хеш по ключу '{key}' не найден или пуст.")
            return None
        except RedisError as e:
            log.exception(f"Ошибка Redis при выполнении hgetall для key='{key}': {e}")
            return None

    async def delete_hash_json(self, key: str) -> None:
        """
        Удаляет весь хеш по ключу.

        Args:
            key (str): Ключ хеша для удаления.
        """
        try:
            await self.redis_client.delete(key)  # type: ignore
            log.debug(f"Хеш по ключу '{key}' удален.")
        except RedisError as e:
            log.exception(f"Ошибка Redis при удалении key='{key}': {e}")

    async def delete_hash_field(self, key: str, field: str) -> None:
        """
        Удаляет одно поле из хеша.

        Args:
            key (str): Ключ хеша.
            field (str): Поле для удаления.
        """
        try:
            await self.redis_client.hdel(key, field)  # type: ignore
            log.debug(f"Поле '{field}' удалено из хеша '{key}'.")
        except RedisError as e:
            log.exception(f"Ошибка Redis при удалении поля '{field}' из key='{key}': {e}")

    async def add_to_set(self, key: str, value: str | int) -> None:
        """
        Добавляет значение в множество.

        Args:
            key (str): Ключ множества.
            value (str | int): Добавляемое значение.
        """
        try:
            await self.redis_client.sadd(key, str(value))  # type: ignore
            log.debug(f"Значение '{value}' добавлено в множество '{key}'.")
        except RedisError as e:
            log.exception(f"Ошибка Redis при добавлении в множество '{key}': {e}")

    async def get_to_set(self, key: str) -> set[str]:
        """
        Возвращает все элементы множества.
        ...
        """
        try:
            # smembers УЖЕ вернет set[bytes]
            members_bytes = await self.redis_client.smembers(key)  # type: ignore
            members = {m.decode("utf-8") for m in members_bytes}
            log.debug(f"Получено {len(members)} элементов из множества '{key}'.")
            return members
        except RedisError as e:
            log.exception(f"Ошибка Redis при получении множества '{key}': {e}")
            return set()

    async def is_set_member(self, key: str, value: str | int) -> bool:
        """
        Проверяет, является ли значение элементом множества.

        Args:
            key (str): Ключ множества.
            value (str | int): Значение для проверки.

        Returns:
            bool: True, если значение является элементом множества, иначе False.
        """
        try:
            is_member = await self.redis_client.sismember(key, str(value))  # type: ignore
            log.debug(f"Проверка принадлежности '{value}' к множеству '{key}': {is_member}.")
            return bool(is_member)
        except RedisError as e:
            log.exception(f"Ошибка Redis при проверке множества '{key}': {e}")
            return False

    async def remove_from_set(self, key: str, value: str | int) -> None:
        """
        Удаляет значение из множества.

        Args:
            key (str): Ключ множества.
            value (str | int): Удаляемое значение.
        """
        try:
            await self.redis_client.srem(key, str(value))  # type: ignore
            log.debug(f"Значение '{value}' удалено из множества '{key}'.")
        except RedisError as e:
            log.exception(f"Ошибка Redis при удалении из множества '{key}': {e}")

    async def key_exists(self, key: str) -> bool:
        """
        Проверяет существование ключа.

        Args:
            key (str): Ключ для проверки.

        Returns:
            bool: True, если ключ существует, иначе False.
        """
        try:
            exists = await self.redis_client.exists(key)  # type: ignore
            log.debug(f"Проверка существования ключа '{key}': {exists}.")
            return bool(exists)
        except RedisError as e:
            log.exception(f"Ошибка Redis при проверке ключа '{key}': {e}")
            return False


# Глобальный экземпляр сервиса для удобного импорта в других частях приложения
redis_service = RedisService(client=redis_client)
