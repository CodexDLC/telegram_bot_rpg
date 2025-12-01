# app/services/core_service/manager/combat_manager.py
from typing import Any

from loguru import logger as log

from app.core.redis_client import redis_client
from app.services.core_service.redis_key import RedisKeys as Rk
from app.services.core_service.redis_service import redis_service


class CombatManager:
    """
    CRUD-менеджер для управления данными боевых сессий в Redis.

    Этот класс предоставляет низкоуровневый API для взаимодействия
    с различными структурами данных Redis, используемыми в бою.
    """

    # --- META (Hash) ---
    async def create_session_meta(self, session_id: str, data: dict) -> None:
        """
        Создает или обновляет метаданные боевой сессии.

        Args:
            session_id (str): Уникальный идентификатор сессии.
            data (dict): Словарь с метаданными (например, `turn_count`, `start_time`).

        Returns:
            None
        """
        key = Rk.get_combat_meta_key(session_id)
        await redis_service.set_hash_fields(key, data)
        log.debug(f"Метаданные для сессии {session_id} сохранены: {data}")

    async def get_session_meta(self, session_id: str) -> dict[str, Any] | None:
        """
        Получает метаданные боевой сессии.

        Args:
            session_id (str): Уникальный идентификатор сессии.

        Returns:
            dict[str, Any] | None: Словарь с метаданными или None, если не найдено.
        """
        key = Rk.get_combat_meta_key(session_id)
        log.debug(f"Запрос метаданных для сессии {session_id}")
        return await redis_service.get_all_hash(key)

    # --- PARTICIPANTS (Set) ---
    async def add_participant_id(self, session_id: str, char_id: int) -> None:
        """
        Добавляет ID персонажа в множество участников сессии.

        Args:
            session_id (str): Уникальный идентификатор сессии.
            char_id (int): ID персонажа для добавления.

        Returns:
            None
        """
        key = Rk.get_combat_participants_key(session_id)
        await redis_service.add_to_set(key, str(char_id))
        log.debug(f"Участник {char_id} добавлен в сессию {session_id}")

    async def get_session_participants(self, session_id: str) -> set[str]:
        """
        Возвращает набор ID всех участников сессии.

        Args:
            session_id (str): Уникальный идентификатор сессии.

        Returns:
            set[str]: Набор строковых ID всех участников.
        """
        key = Rk.get_combat_participants_key(session_id)
        log.debug(f"Запрос списка участников для сессии {session_id}")
        return await redis_service.get_to_set(key)

    # --- ACTOR (JSON String) ---
    async def save_actor_json(self, session_id: str, char_id: int, json_data: str) -> None:
        """
        Сохраняет состояние бойца (DTO) в виде JSON-строки.

        Args:
            session_id (str): Уникальный идентификатор сессии.
            char_id (int): ID персонажа (бойца).
            json_data (str): JSON-строка с состоянием бойца.

        Returns:
            None
        """
        key = Rk.get_combat_actor_key(session_id, char_id)
        await redis_client.set(key, json_data)
        log.debug(f"Состояние бойца {char_id} в сессии {session_id} сохранено.")

    async def get_actor_json(self, session_id: str, char_id: int) -> str | None:
        """
        Получает состояние бойца (DTO) в виде JSON-строки.

        Args:
            session_id (str): Уникальный идентификатор сессии.
            char_id (int): ID персонажа (бойца).

        Returns:
            str | None: JSON-строка с состоянием или None, если не найдено.
        """
        key = Rk.get_combat_actor_key(session_id, char_id)
        log.debug(f"Запрос состояния бойца {char_id} в сессии {session_id}")
        return await redis_client.get(key)

    async def set_pending_move(self, session_id: str, actor_id: int, target_id: int, move_data: str) -> None:
        """Сохраняет ход для КОНКРЕТНОЙ пары."""
        key = Rk.get_combat_pending_move_key(session_id, actor_id, target_id)
        await redis_client.set(key, move_data)
        log.debug(f"Ход {actor_id}->{target_id} в сессии {session_id} сохранен.")

    async def get_pending_move(self, session_id: str, actor_id: int, target_id: int) -> str | None:
        """Получает ход для КОНКРЕТНОЙ пары."""
        key = Rk.get_combat_pending_move_key(session_id, actor_id, target_id)
        return await redis_client.get(key)

    async def delete_pending_move(self, session_id: str, actor_id: int, target_id: int) -> None:
        """Удаляет ход для КОНКРЕТНОЙ пары."""
        key = Rk.get_combat_pending_move_key(session_id, actor_id, target_id)
        await redis_client.delete(key)

    async def delete_all_pending_moves_for_actor(self, session_id: str, actor_id: int) -> None:
        """Удаляет ВСЕ заявки игрока (ко всем врагам)."""
        pattern = Rk.get_combat_pending_move_pattern(session_id, actor_id)
        # Используем scan_iter для безопасного поиска без блокировки Redis
        keys = [key async for key in redis_client.scan_iter(match=pattern)]
        if keys:
            await redis_client.delete(*keys)
            log.debug(f"Удалены все ходы игрока {actor_id} в сессии {session_id} ({len(keys)} шт).")

    # --- LOGS (List) ---
    async def push_combat_log(self, session_id: str, log_entry_json: str) -> None:
        """
        Добавляет запись в лог боя.

        Args:
            session_id (str): Уникальный идентификатор сессии.
            log_entry_json (str): JSON-строка с записью лога.

        Returns:
            None
        """
        key = Rk.get_combat_log_key(session_id)
        await redis_client.rpush(key, log_entry_json)
        log.debug(f"Новая запись добавлена в лог сессии {session_id}")

    async def get_combat_log_list(self, session_id: str) -> list[str]:
        """
        Возвращает все записи из лога боя.

        Args:
            session_id (str): Уникальный идентификатор сессии.

        Returns:
            list[str]: Список JSON-строк с записями лога.
        """
        key = Rk.get_combat_log_key(session_id)
        log.debug(f"Запрос полного лога для сессии {session_id}")
        return await redis_client.lrange(key, 0, -1)

    async def set_player_status(self, char_id: int, status: str, ttl: int = 300) -> None:
        """Устанавливает статус игрока (например, ссылка на бой)."""
        key = Rk.get_player_status_key(char_id)
        await redis_service.set_value(key, status, ttl=ttl)

    async def get_player_status(self, char_id: int) -> str | None:
        key = Rk.get_player_status_key(char_id)
        return await redis_service.get_value(key)

    async def delete_player_status(self, char_id: int) -> None:
        key = Rk.get_player_status_key(char_id)
        await redis_service.delete_key(key)


combat_manager = CombatManager()
