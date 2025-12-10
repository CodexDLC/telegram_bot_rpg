from typing import Any

from apps.common.services.core_service.redis_key import RedisKeys as Rk
from apps.common.services.core_service.redis_service import RedisService


class CombatManager:
    """
    Менеджер для управления данными боевых сессий в Redis.

    Предоставляет CRUD-операции для метаданных боя, участников,
    состояний акторов, ожидающих ходов и логов боя.
    """

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    async def create_session_meta(self, session_id: str, data: dict[str, Any]) -> None:
        """
        Создает или обновляет метаданные боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            data: Словарь с метаданными (например, тип боя, статус активности).
        """
        key = Rk.get_combat_meta_key(session_id)
        await self.redis_service.set_hash_fields(key, data)

    async def get_session_meta(self, session_id: str) -> dict[str, str] | None:
        """
        Получает все метаданные боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.

        Returns:
            Словарь с метаданными сессии, или None, если метаданные не найдены.
        """
        key = Rk.get_combat_meta_key(session_id)
        return await self.redis_service.get_all_hash(key)

    async def add_participant_id(self, session_id: str, char_id: int) -> None:
        """
        Добавляет идентификатор персонажа в список участников боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            char_id: Идентификатор персонажа-участника.
        """
        key = Rk.get_combat_participants_key(session_id)
        await self.redis_service.add_to_set(key, str(char_id))

    async def get_session_participants(self, session_id: str) -> set[str]:
        """
        Получает список всех участников боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.

        Returns:
            Множество строковых идентификаторов участников.
        """
        key = Rk.get_combat_participants_key(session_id)
        return await self.redis_service.get_to_set(key)

    async def save_actor_json(self, session_id: str, char_id: int, json_data: str) -> None:
        """
        Сохраняет JSON-строку с данными актора в боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            char_id: Идентификатор актора (персонажа).
            json_data: JSON-строка с данными актора.
        """
        key = Rk.get_combat_actor_key(session_id, char_id)
        await self.redis_service.set_value(key, json_data)

    async def get_actor_json(self, session_id: str, char_id: int) -> str | None:
        """
        Получает JSON-строку с данными актора из боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            char_id: Идентификатор актора (персонажа).

        Returns:
            JSON-строка с данными актора, или None, если данные не найдены.
        """
        key = Rk.get_combat_actor_key(session_id, char_id)
        return await self.redis_service.get_value(key)

    async def set_pending_move(self, session_id: str, actor_id: int, target_id: int, move_data: str) -> None:
        """
        Сохраняет данные ожидающего хода актора против цели в боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            actor_id: Идентификатор актора, совершающего ход.
            target_id: Идентификатор цели хода.
            move_data: Строка с данными хода.
        """
        key = Rk.get_combat_pending_move_key(session_id, actor_id, target_id)
        await self.redis_service.set_value(key, move_data)

    async def get_pending_move(self, session_id: str, actor_id: int, target_id: int) -> str | None:
        """
        Получает данные ожидающего хода актора против цели в боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            actor_id: Идентификатор актора, совершающего ход.
            target_id: Идентификатор цели хода.

        Returns:
            Строка с данными хода, или None, если ход не найден.
        """
        key = Rk.get_combat_pending_move_key(session_id, actor_id, target_id)
        return await self.redis_service.get_value(key)

    async def delete_pending_move(self, session_id: str, actor_id: int, target_id: int) -> None:
        """
        Удаляет данные ожидающего хода актора против цели в боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            actor_id: Идентификатор актора, совершившего ход.
            target_id: Идентификатор цели хода.
        """
        key = Rk.get_combat_pending_move_key(session_id, actor_id, target_id)
        await self.redis_service.delete_key(key)

    async def delete_all_pending_moves_for_actor(self, session_id: str, actor_id: int) -> None:
        """
        Удаляет все ожидающие ходы, инициированные указанным актором в боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            actor_id: Идентификатор актора, чьи ходы нужно удалить.
        """
        pattern = Rk.get_combat_pending_move_pattern(session_id, actor_id)
        await self.redis_service.delete_by_pattern(pattern)

    async def push_combat_log(self, session_id: str, log_entry_json: str) -> None:
        """
        Добавляет JSON-строку с записью лога в список логов боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.
            log_entry_json: JSON-строка с записью лога.
        """
        key = Rk.get_combat_log_key(session_id)
        await self.redis_service.push_to_list(key, log_entry_json)

    async def get_combat_log_list(self, session_id: str) -> list[str]:
        """
        Получает все записи лога боевой сессии.

        Args:
            session_id: Уникальный идентификатор боевой сессии.

        Returns:
            Список JSON-строк, представляющих записи лога.
        """
        key = Rk.get_combat_log_key(session_id)
        return await self.redis_service.get_list_range(key)

    async def set_player_status(self, char_id: int, status: str, ttl: int = 300) -> None:
        """
        Устанавливает текущий статус игрока для межсервисного взаимодействия.

        Args:
            char_id: Идентификатор персонажа.
            status: Строка, описывающая статус (например, 'combat:session_id', 'arena:queue').
            ttl: Время жизни статуса в секундах. По умолчанию 300 секунд (5 минут).
        """
        key = Rk.get_player_status_key(char_id)
        await self.redis_service.set_value(key, status, ttl=ttl)

    async def get_player_status(self, char_id: int) -> str | None:
        """
        Получает текущий статус игрока.

        Args:
            char_id: Идентификатор персонажа.

        Returns:
            Строка, описывающая статус, или None, если статус не установлен.
        """
        key = Rk.get_player_status_key(char_id)
        return await self.redis_service.get_value(key)

    async def delete_player_status(self, char_id: int) -> None:
        """
        Удаляет текущий статус игрока.

        Args:
            char_id: Идентификатор персонажа.
        """
        key = Rk.get_player_status_key(char_id)
        await self.redis_service.delete_key(key)
