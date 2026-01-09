import json
from typing import Any

from loguru import logger as log
from redis.asyncio.client import Pipeline

from apps.common.services.redis.redis_fields import AccountFields as Af
from apps.common.services.redis.redis_key import RedisKeys as Rk
from apps.common.services.redis.redis_service import RedisService


class AccountManager:
    """
    Менеджер для управления данными аккаунтов в Redis.
    Использует RedisService для выполнения операций.
    """

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    def _serialize_value(self, value: Any) -> str | int | float:
        """Сериализует значение для сохранения в Redis."""
        if isinstance(value, (dict, list, bool)):
            return json.dumps(value)
        return value

    async def create_account(self, char_id: int, initial_data: dict[str, Any]) -> None:
        """
        Создает запись аккаунта в Redis.
        """
        key = Rk.get_account_key(char_id)
        serialized_data = {k: self._serialize_value(v) for k, v in initial_data.items()}
        await self.redis_service.set_hash_fields(key, serialized_data)
        log.info(f"AccountManager | action=create status=success char_id={char_id}")

    async def account_exists(self, char_id: int) -> bool:
        """
        Проверяет существование аккаунта.
        """
        key = Rk.get_account_key(char_id)
        return await self.redis_service.key_exists(key)

    async def get_account_data(self, char_id: int) -> dict[str, Any] | None:
        """
        Получает все данные аккаунта и десериализует их.
        """
        key = Rk.get_account_key(char_id)
        raw_data = await self.redis_service.get_all_hash(key)
        if not raw_data:
            return None

        deserialized_data = {}
        for k, v in raw_data.items():
            try:
                # Пытаемся десериализовать JSON
                if v and (v.startswith("{") or v.startswith("[") or v in ("true", "false")):
                    deserialized_data[k] = json.loads(v)
                else:
                    deserialized_data[k] = v
            except (json.JSONDecodeError, TypeError):
                deserialized_data[k] = v
        return deserialized_data

    async def get_account_field(self, char_id: int, field: str) -> Any | None:
        """
        Получает значение одного поля аккаунта.
        Автоматически десериализует JSON, если это возможно.
        """
        key = Rk.get_account_key(char_id)
        value = await self.redis_service.get_hash_field(key, field)

        if value is None:
            return None

        # Пытаемся определить, является ли значение JSON-ом
        if value and (value.startswith("{") or value.startswith("[") or value in ("true", "false")):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        # Пытаемся привести к числу
        if value.isdigit():
            return int(value)
        try:
            return float(value)
        except ValueError:
            return value

    async def get_account_json(self, char_id: int, field: str) -> dict | list | None:
        """
        Получает JSON-поле аккаунта (явная десериализация).
        """
        key = Rk.get_account_key(char_id)
        return await self.redis_service.get_hash_json(key, field)

    async def update_account_fields(self, char_id: int, updates: dict[str, Any]) -> None:
        """
        Обновляет несколько полей аккаунта.
        """
        key = Rk.get_account_key(char_id)
        serialized_updates = {k: self._serialize_value(v) for k, v in updates.items()}
        await self.redis_service.set_hash_fields(key, serialized_updates)
        log.debug(f"AccountManager | action=update char_id={char_id} fields={list(updates.keys())}")

    async def delete_account_field(self, char_id: int, field: str) -> None:
        """
        Удаляет одно поле из аккаунта.
        """
        key = Rk.get_account_key(char_id)
        await self.redis_service.delete_hash_field(key, field)

    async def get_accounts_json_batch(self, char_ids: list[int], field: str) -> list[Any | None]:
        """
        Массовое получение JSON-поля для списка аккаунтов через сервис.
        """
        if not char_ids:
            return []

        def _fill_pipeline(pipe: Pipeline) -> None:
            for char_id in char_ids:
                key = Rk.get_account_key(char_id)
                pipe.hget(key, field)

        results = await self.redis_service.execute_pipeline(_fill_pipeline)

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

    async def bulk_link_combat_session(self, char_ids: list[int], session_id: str) -> None:
        """
        Массово устанавливает поле combat_session_id у списка игроков.
        """
        if not char_ids:
            return

        def _fill_link(pipe: Pipeline) -> None:
            for pid in char_ids:
                key = Rk.get_account_key(pid)
                pipe.hset(key, Af.COMBAT_SESSION_ID, session_id)

        await self.redis_service.execute_pipeline(_fill_link)
        log.debug(f"AccountManager | linked combat session {session_id} for {len(char_ids)} chars")

    async def bulk_unlink_combat_session(self, char_ids: list[int]) -> None:
        """
        Массово удаляет поле combat_session_id у списка игроков.
        """
        if not char_ids:
            return

        def _fill_unlink(pipe: Pipeline) -> None:
            for pid in char_ids:
                key = Rk.get_account_key(pid)
                pipe.hdel(key, Af.COMBAT_SESSION_ID)

        await self.redis_service.execute_pipeline(_fill_unlink)
        log.debug(f"AccountManager | unlinked combat session for {len(char_ids)} chars")
