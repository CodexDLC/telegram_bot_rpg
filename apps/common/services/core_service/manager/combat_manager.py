from typing import Any

from loguru import logger as log
from redis.asyncio.client import Pipeline

from apps.common.services.core_service.redis_key import RedisKeys as Rk
from apps.common.services.core_service.redis_service import RedisService


class CombatManager:
    """
    Менеджер для управления данными боевых сессий в Redis.
    """

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    # --- RBC Methods (New) ---

    async def get_rbc_actor_state_json(self, session_id: str, char_id: int) -> str | None:
        key = Rk.get_combat_actors_key(session_id)
        return await self.redis_service.get_hash_field(key, str(char_id))

    async def set_rbc_actor_state_json(self, session_id: str, char_id: int, json_data: str) -> None:
        key = Rk.get_combat_actors_key(session_id)
        await self.redis_service.set_hash_fields(key, {str(char_id): json_data})

    async def get_rbc_all_actors_json(self, session_id: str) -> dict[str, str] | None:
        key = Rk.get_combat_actors_key(session_id)
        return await self.redis_service.get_all_hash(key)

    async def register_rbc_move(self, session_id: str, char_id: int, target_id: int, move_json: str) -> None:
        key = Rk.get_combat_moves_key(session_id, char_id)
        await self.redis_service.set_hash_fields(key, {str(target_id): move_json})

    async def get_rbc_next_target_id(self, session_id: str, char_id: int) -> int | None:
        key = Rk.get_combat_exchanges_key(session_id, char_id)
        result = await self.redis_service.get_list_range(key, 0, 0)
        if not result:
            return None
        return int(result[0])

    async def get_rbc_queue_length(self, session_id: str, char_id: int) -> int:
        """Возвращает длину очереди обменов для игрока."""
        key = Rk.get_combat_exchanges_key(session_id, char_id)
        return await self.redis_service.get_list_length(key)

    async def get_exchange_queue_list(self, session_id: str, char_id: int) -> list[str]:
        """
        Возвращает полный список ID противников из очереди обменов.
        Используется для ViewService.
        """
        key = Rk.get_combat_exchanges_key(session_id, char_id)
        return await self.redis_service.get_list_range(key, 0, -1)

    async def pop_from_exchange_queue(self, session_id: str, char_id: int) -> str | None:
        """Извлекает первого противника из очереди обменов."""
        key = Rk.get_combat_exchanges_key(session_id, char_id)
        return await self.redis_service.pop_from_list_left(key)

    async def get_rbc_moves(self, session_id: str, char_id: int) -> dict[str, str] | None:
        key = Rk.get_combat_moves_key(session_id, char_id)
        return await self.redis_service.get_all_hash(key)

    async def remove_rbc_move(self, session_id: str, char_id: int, target_id: int) -> None:
        key = Rk.get_combat_moves_key(session_id, char_id)
        await self.redis_service.delete_hash_field(key, str(target_id))

    async def push_to_exchange_queue(self, session_id: str, char_id: int, target_id: int) -> None:
        """RBC: Добавляет противника в конец очереди обменов."""
        key = Rk.get_combat_exchanges_key(session_id, char_id)
        await self.redis_service.push_to_list(key, str(target_id))

    async def add_enemies_to_exchange_queue(self, session_id: str, char_id: int, enemies_ids: list[str]) -> None:
        """
        RBC: Добавляет список противников в конец очереди обменов.
        Оптимизировано через Pipeline (Batch RPUSH).
        """
        if not enemies_ids:
            return

        key = Rk.get_combat_exchanges_key(session_id, char_id)

        # Функция-сборщик для пайплайна
        def _fill_queue(pipe: Pipeline) -> None:
            # RPUSH в Redis умеет принимать много значений сразу (*args)
            pipe.rpush(key, *enemies_ids)

        # Отправляем в сервис
        await self.redis_service.execute_pipeline(_fill_queue)

    async def create_rbc_session_meta(self, session_id: str, data: dict[str, Any]) -> None:
        """RBC: Создает или обновляет метаданные сессии."""
        key = Rk.get_rbc_meta_key(session_id)
        await self.redis_service.set_hash_fields(key, data)

    async def get_rbc_session_meta(self, session_id: str) -> dict[str, str] | None:
        """RBC: Получает метаданные сессии."""
        key = Rk.get_rbc_meta_key(session_id)
        return await self.redis_service.get_all_hash(key)

    async def cleanup_rbc_session(self, session_id: str, history_ttl: int = 86400) -> None:
        """
        RBC: Очищает оперативные данные сессии и выставляет TTL для исторических данных.
        Оптимизировано через Pipeline.
        """
        log.info(f"CombatManager | action=cleanup_rbc_session session_id='{session_id}'")

        # 1. Читаем список участников (GET запрос делаем отдельно, т.к. результат нужен для логики ниже)
        actors_data = await self.get_rbc_all_actors_json(session_id)

        # 2. Наполняем пайплайн командами удаления и продления жизни
        def _fill_cleanup(pipe: Pipeline) -> None:
            # Удаляем очереди и мувы участников
            if actors_data:
                for pid_str in actors_data:
                    try:
                        pid = int(pid_str)
                        pipe.delete(Rk.get_combat_exchanges_key(session_id, pid))
                        pipe.delete(Rk.get_combat_moves_key(session_id, pid))
                    except ValueError:
                        continue

            # Выставляем TTL для исторических данных (мета, акторы, логи)
            pipe.expire(Rk.get_rbc_meta_key(session_id), history_ttl)
            pipe.expire(Rk.get_combat_actors_key(session_id), history_ttl)
            pipe.expire(Rk.get_combat_log_key(session_id), history_ttl)

        # 3. Выполняем всё разом
        await self.redis_service.execute_pipeline(_fill_cleanup)

    async def get_all_active_session_ids(self) -> list[str]:
        """
        RBC: Сканирует Redis и возвращает список ID всех активных сессий.
        Используется для восстановления работы воркеров после перезагрузки.
        """
        active_sessions = []
        # Паттерн для поиска всех мета-ключей RBC
        pattern = "combat:rbc:*:meta"

        # Используем scan_iter для безопасного перебора ключей
        async for key in self.redis_service.redis_client.scan_iter(match=pattern):
            # Извлекаем session_id из ключа (combat:rbc:{UUID}:meta)
            try:
                # key.split(":") -> ['combat', 'rbc', '{UUID}', 'meta']
                parts = key.split(":")
                if len(parts) != 4:
                    continue
                session_id = parts[2]

                # Проверяем флаг active
                is_active = await self.redis_service.get_hash_field(key, "active")
                if is_active == "1":
                    active_sessions.append(session_id)
            except Exception as e:  # noqa: BLE001
                log.error(f"CombatManager | Error scanning session key {key}: {e}")
                continue

        return active_sessions

    # --- Legacy Methods ---

    async def create_session_meta(self, session_id: str, data: dict[str, Any]) -> None:
        key = Rk.get_combat_meta_key(session_id)
        await self.redis_service.set_hash_fields(key, data)

    async def get_session_meta(self, session_id: str) -> dict[str, str] | None:
        key = Rk.get_combat_meta_key(session_id)
        return await self.redis_service.get_all_hash(key)

    async def add_participant_id(self, session_id: str, char_id: int) -> None:
        key = Rk.get_combat_participants_key(session_id)
        await self.redis_service.add_to_set(key, str(char_id))

    async def get_session_participants(self, session_id: str) -> set[str]:
        key = Rk.get_combat_participants_key(session_id)
        return await self.redis_service.get_set_members(key)

    async def save_actor_json(self, session_id: str, char_id: int, json_data: str) -> None:
        key = Rk.get_combat_actor_key(session_id, char_id)
        await self.redis_service.set_value(key, json_data)

    async def get_actor_json(self, session_id: str, char_id: int) -> str | None:
        key = Rk.get_combat_actor_key(session_id, char_id)
        return await self.redis_service.get_value(key)

    async def set_pending_move(
        self, session_id: str, actor_id: int, target_id: int, move_data: str, timeout: int
    ) -> None:
        key = Rk.get_combat_pending_move_key(session_id, actor_id, target_id)
        await self.redis_service.set_value(key, move_data, ttl=timeout)

    async def get_pending_move(self, session_id: str, actor_id: int, target_id: int) -> str | None:
        key = Rk.get_combat_pending_move_key(session_id, actor_id, target_id)
        return await self.redis_service.get_value(key)

    async def delete_pending_move(self, session_id: str, actor_id: int, target_id: int) -> None:
        key = Rk.get_combat_pending_move_key(session_id, actor_id, target_id)
        await self.redis_service.delete_key(key)

    async def delete_all_pending_moves_for_actor(self, session_id: str, actor_id: int) -> None:
        pattern = Rk.get_combat_pending_move_pattern(session_id, actor_id)
        await self.redis_service.delete_by_pattern(pattern)

    async def push_combat_log(self, session_id: str, log_entry_json: str) -> None:
        key = Rk.get_combat_log_key(session_id)
        await self.redis_service.push_to_list(key, log_entry_json)

    async def get_combat_log_list(self, session_id: str) -> list[str]:
        key = Rk.get_combat_log_key(session_id)
        return await self.redis_service.get_list_range(key)

    async def set_player_status(self, char_id: int, status: str, ttl: int = 300) -> None:
        key = Rk.get_player_status_key(char_id)
        await self.redis_service.set_value(key, status, ttl=ttl)

    async def get_player_status(self, char_id: int) -> str | None:
        key = Rk.get_player_status_key(char_id)
        return await self.redis_service.get_value(key)

    async def delete_player_status(self, char_id: int) -> None:
        key = Rk.get_player_status_key(char_id)
        await self.redis_service.delete_key(key)
