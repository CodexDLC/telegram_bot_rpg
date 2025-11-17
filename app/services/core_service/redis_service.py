# app/services/core_service/redis_service.py
from loguru import logger as log
import json
from redis.asyncio import Redis
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

    async def set_hash_json(self, key: str, field: str, data: dict):
        """
        Сериализует словарь в JSON и сохраняет его в поле хеша.

        Args:
            key (str): Ключ хеша в Redis.
            field (str): Поле внутри хеша.
            data (dict): Словарь для сохранения.
        """
        try:
            data_json = json.dumps(data)
            await self.redis_client.hset(key, field, data_json)
            log.debug(f"Установлено значение для key='{key}', field='{field}'.")
        except TypeError as e:
            log.error(f"Ошибка сериализации JSON для key='{key}', field='{field}': {e}")
        except Exception as e:
            log.exception(f"Ошибка Redis при выполнении hset для key='{key}': {e}")

    async def set_hash_fields(self, key: str, data: dict):
        """
        Устанавливает НЕСКОЛЬКО полей в хеше за один вызов.
        Идеально для обновления 'state' и 'location_id' ОДНОВРЕМЕННО.
        """
        try:
            # hset может принимать mapping (словарь)
            await self.redis_client.hset(key, mapping=data)
            log.debug(f"Установлены поля {data.keys()} для key='{key}'.")
        except Exception as e:
            log.exception(f"Ошибка Redis при выполнении hset (mapping) для key='{key}': {e}")

    async def get_hash_json(self, key: str, field: str) -> dict | None:
        """
        Получает JSON-строку из поля хеша и десериализует ее в словарь.

        Args:
            key (str): Ключ хеша.
            field (str): Поле внутри хеша.

        Returns:
            dict | None: Десериализованный словарь, если данные существуют, иначе None.
        """
        try:
            data_json = await self.redis_client.hget(key, field)
            if data_json:
                log.debug(f"Найдено значение для key='{key}', field='{field}'.")
                return json.loads(data_json)
            log.debug(f"Значение для key='{key}', field='{field}' не найдено.")
            return None
        except json.JSONDecodeError as e:
            log.error(f"Ошибка десериализации JSON для key='{key}', field='{field}': {e}")
            return None
        except Exception as e:
            log.exception(f"Ошибка Redis при выполнении hget для key='{key}': {e}")
            return None

    async def get_hash_field(self, key: str, field: str):
        """
        Получает одно поле из хеша.
        ...
        """

        try:
            value = await self.redis_client.hget(key, field)
            if value:
                log.debug(f"Получено значение для key='{key}', field='{field}'.")
                return value
            log.debug(f"Значение для key='{key}', field='{field}' не найдено.")
            return None
        except Exception as e:
            log.exception(f"Ошибка Redis при выполнении hget для key='{key}': {e}")
            return None


    async def get_all_hash(self, key: str) -> dict | None:
        """
        Получает все поля и значения из хеша.
        ...
        """
        try:
            data_dict = await self.redis_client.hgetall(key)
            if data_dict:
                log.debug(f"Получены все поля для key='{key}'.")
                return data_dict
            log.debug(f"Хеш по ключу '{key}' не найден или пуст.")
            return None
        except Exception as e:
            log.exception(f"Ошибка Redis при выполнении hgetall для key='{key}': {e}")
            return None

    async def delete_hash_json(self, key: str):
        """
        Удаляет весь хеш по ключу.

        Args:
            key (str): Ключ хеша для удаления.
        """
        try:
            await self.redis_client.delete(key)
            log.debug(f"Хеш по ключу '{key}' удален.")
        except Exception as e:
            log.exception(f"Ошибка Redis при удалении key='{key}': {e}")

    async def delete_hash_field(self, key: str, field: str):
        """
        Удаляет одно поле из хеша.

        Args:
            key (str): Ключ хеша.
            field (str): Поле для удаления.
        """
        try:
            await self.redis_client.hdel(key, field)
            log.debug(f"Поле '{field}' удалено из хеша '{key}'.")
        except Exception as e:
            log.exception(f"Ошибка Redis при удалении поля '{field}' из key='{key}': {e}")

    async def add_to_set(self, key: str, value: str | int):
        """
        Добавляет значение в множество.

        Args:
            key (str): Ключ множества.
            value (str | int): Добавляемое значение.
        """
        try:
            await self.redis_client.sadd(key, str(value))
            log.debug(f"Значение '{value}' добавлено в множество '{key}'.")
        except Exception as e:
            log.exception(f"Ошибка Redis при добавлении в множество '{key}': {e}")

    async def get_to_set(self, key: str) -> set:
        """
        Возвращает все элементы множества.
        ...
        """
        try:
            # smembers УЖЕ вернет set[str]
            members = await self.redis_client.smembers(key)
            log.debug(f"Получено {len(members)} элементов из множества '{key}'.")
            return members  # <--- Просто возвращаем множество
        except Exception as e:
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
            is_member = await self.redis_client.sismember(key, str(value))
            log.debug(f"Проверка принадлежности '{value}' к множеству '{key}': {is_member}.")
            return is_member
        except Exception as e:
            log.exception(f"Ошибка Redis при проверке множества '{key}': {e}")
            return False

    async def remove_from_set(self, key: str, value: str | int):
        """
        Удаляет значение из множества.

        Args:
            key (str): Ключ множества.
            value (str | int): Удаляемое значение.
        """
        try:
            await self.redis_client.srem(key, str(value))
            log.debug(f"Значение '{value}' удалено из множества '{key}'.")
        except Exception as e:
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
            exists = await self.redis_client.exists(key) > 0
            log.debug(f"Проверка существования ключа '{key}': {exists}.")
            return exists
        except Exception as e:
            log.exception(f"Ошибка Redis при проверке ключа '{key}': {e}")
            return False

# Глобальный экземпляр сервиса для удобного импорта в других частях приложения
redis_service = RedisService(client=redis_client)
