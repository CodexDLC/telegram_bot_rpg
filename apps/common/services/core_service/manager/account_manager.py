import json
from typing import Any

from loguru import logger as log

from apps.common.services.core_service.redis_key import RedisKeys as Rk
from apps.common.services.core_service.redis_service import RedisService


class AccountManager:
    """
    Менеджер для управления данными аккаунтов персонажей в Redis.

    Предоставляет методы для создания, получения, обновления и проверки
    существования данных аккаунта, используя хеши Redis с ключом 'ac:{char_id}'.
    Автоматически обрабатывает сериализацию сложных типов данных (JSON).
    """

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    def _serialize_value(self, value: Any) -> str:
        """
        Приватный метод: превращает любое значение в строку для Redis.
        - dict/list -> JSON string
        - bool -> 'true'/'false'
        - None -> '' (или можно пропускать)
        - Остальное -> str(value)
        """
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, bool):
            return str(value).lower()
        return str(value)

    def _prepare_data_for_redis(self, data: dict[str, Any]) -> dict[str, str]:
        """
        Приватный метод: подготавливает словарь для массовой записи.
        """
        return {k: self._serialize_value(v) for k, v in data.items()}

    async def create_account(self, char_id: int, data: dict[str, Any]) -> None:
        """
        Создает или полностью перезаписывает хеш аккаунта.
        Автоматически сериализует значения.
        """
        key = Rk.get_account_key(char_id)
        prepared_data = self._prepare_data_for_redis(data)
        await self.redis_service.set_hash_fields(key, prepared_data)

    async def update_account_fields(self, char_id: int, data: dict[str, Any]) -> None:
        """
        Массовое обновление полей.
        Автоматически сериализует значения.
        """
        key = Rk.get_account_key(char_id)
        prepared_data = self._prepare_data_for_redis(data)
        await self.redis_service.set_hash_fields(key, prepared_data)

    async def set_account_field(self, char_id: int, field: str, value: Any) -> None:
        """
        Точечное обновление одного поля.
        Сам определяет тип value (str, int, dict, list) и сериализует его при необходимости.
        """
        key = Rk.get_account_key(char_id)
        serialized_value = self._serialize_value(value)
        # Используем update_account_fields или прямой вызов redis_service,
        # но для консистентности проще вызвать set_hash_fields с одним полем.
        await self.redis_service.set_hash_fields(key, {field: serialized_value})

    async def get_account_data(self, char_id: int) -> dict[str, str] | None:
        """
        Получает все данные аккаунта (значения остаются строками, как в Redis).
        """
        key = Rk.get_account_key(char_id)
        return await self.redis_service.get_all_hash(key)

    async def get_account_field(self, char_id: int, field: str) -> str | None:
        """
        Получает значение поля как строку.
        """
        key = Rk.get_account_key(char_id)
        return await self.redis_service.get_hash_field(key, field)

    async def get_account_json(self, char_id: int, field: str) -> Any | None:
        """
        Получает значение поля и пытается десериализовать его из JSON.
        Использовать, если вы точно знаете, что там лежит dict или list.
        """
        raw_data = await self.get_account_field(char_id, field)
        if not raw_data:
            return None
        try:
            return json.loads(raw_data)
        except json.JSONDecodeError:
            log.error(f"AccountManager | action=get_account_json status=failed_decode char_id={char_id} field={field}")
            return None

    async def get_accounts_json_batch(self, char_ids: list[int], field: str) -> list[Any | None]:
        """
        Массовое получение JSON-поля для списка аккаунтов.
        Использует Pipeline для оптимизации сетевых запросов.
        """
        if not char_ids:
            return []

        # Доступ к redis_client через сервис
        async with self.redis_service.redis_client.pipeline() as pipe:
            for char_id in char_ids:
                key = Rk.get_account_key(char_id)
                pipe.hget(key, field)
            results = await pipe.execute()

        parsed_results = []
        for res in results:
            if res:
                try:
                    parsed_results.append(json.loads(res))
                except json.JSONDecodeError:
                    log.error(f"AccountManager | batch_decode_fail field={field}")
                    parsed_results.append(None)
            else:
                parsed_results.append(None)

        return parsed_results

    async def delete_account_field(self, char_id: int, field: str) -> None:
        """
        Удаляет поле.
        """
        key = Rk.get_account_key(char_id)
        await self.redis_service.delete_hash_field(key, field)

    async def account_exists(self, char_id: int) -> bool:
        """
        Проверяет существование аккаунта.
        """
        key = Rk.get_account_key(char_id)
        return await self.redis_service.key_exists(key)
