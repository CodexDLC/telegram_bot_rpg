# apps/game_core/game_service/scenario_orchestrator/logic/scenario_manager.py
import json
import uuid
from typing import Any

from loguru import logger as log

from apps.common.database.db_contract.i_scenario_repo import IScenarioRepository
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.redis_service import RedisService


class ScenarioManager:
    """
    Фасад данных.
    Централизованно управляет состоянием сессии (Redis + SQL Backup).
    Скрывает детали хранения от Оркестратора.
    """

    def __init__(self, redis_service: RedisService, repo: IScenarioRepository, account_manager: AccountManager):
        self.redis = redis_service
        self.repo = repo
        self.account_manager = account_manager

    # --- 1. Работа с сессией (Умная загрузка) ---

    async def register_new_session(self, char_id: int, quest_key: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Создает новую сессию: генерирует UUID, обновляет аккаунт и сохраняет контекст.
        Используется Хендлерами при инициализации.
        """
        session_id = uuid.uuid4()
        session_id_str = str(session_id)

        # 1. Обновляем статус аккаунта
        await self.update_account_state(char_id, quest_key, session_id_str)

        # 2. Обогащаем контекст системными данными
        context["scenario_session_id"] = session_id_str
        context["quest_key"] = quest_key
        if "step_counter" not in context:
            context["step_counter"] = 0

        # 3. Сохраняем в Redis
        await self.save_session_context(char_id, context)

        return context

    async def load_session(self, char_id: int) -> dict[str, Any]:
        """
        Пытается загрузить сессию из Redis.
        Если Redis пуст — пытается восстановить из БД (Backup).
        Возвращает пустой dict, если сессии нет нигде.
        """
        # 1. Пробуем Redis (быстро)
        context = await self.get_session_context(char_id)

        # 2. Если пусто, пробуем БД (медленно, но надежно)
        if not context:
            log.info(f"Manager | session_miss char={char_id}. Checking DB backup...")
            db_state = await self.repo.get_active_state(char_id)

            if db_state:
                context = db_state.get("context", {})
                # Самолечение: возвращаем данные в Redis для следующих шагов
                if context:
                    await self.save_session_context(char_id, context)
                    log.success(f"Manager | session_restored from DB char={char_id}")
            else:
                log.warning(f"Manager | session_not_found anywhere char={char_id}")

        return context

    async def get_session_context(self, char_id: int) -> dict[str, Any]:
        """Прямое получение из Redis (без фоллбэка в БД)."""
        key = f"scen:session:{char_id}:data"
        raw_data = await self.redis.get_all_hash(key)
        if not raw_data:
            return {}

        context: dict[str, Any] = {}
        for k, v in raw_data.items():
            if v == "null":
                context[k] = None
                continue

            try:
                # Пытаемся десериализовать JSON (для списков и словарей)
                context[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                # Простая типизация для плоских значений
                if v.isdigit():
                    context[k] = int(v)
                else:
                    try:
                        context[k] = float(v)
                    except ValueError:
                        context[k] = v
        return context

    async def save_session_context(self, char_id: int, context: dict[str, Any], ttl: int = 86400):
        """Сохранение в Redis."""
        key = f"scen:session:{char_id}:data"
        if not context:
            return

        processed_context = {}
        for k, v in context.items():
            if v is None:
                # Redis не принимает None. Сохраняем как 'null' (строка).
                processed_context[k] = "null"
            elif isinstance(v, (dict, list, bool)):
                # bool тоже лучше в json, чтобы True -> 'true'
                processed_context[k] = json.dumps(v)
            else:
                # Все остальное (числа, строки) сохраняем как есть
                processed_context[k] = v

        await self.redis.set_hash_fields(key, processed_context)
        await self.redis.expire(key, ttl)

    async def clear_session(self, char_id: int):
        """Удаляет сессию из Redis."""
        await self.redis.delete_key(f"scen:session:{char_id}:data")

    # --- 2. Контент (Nodes / Master) ---

    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        return await self.repo.get_node(quest_key, node_key)

    async def get_quest_master(self, quest_key: str) -> dict[str, Any] | None:
        return await self.repo.get_master(quest_key)

    async def get_nodes_by_pool(self, quest_key: str, pool_tag: str) -> list[dict[str, Any]]:
        return await self.repo.get_nodes_by_pool(quest_key, pool_tag)

    # --- 3. Аккаунт и Бэкапы ---

    async def update_account_state(self, char_id: int, quest_key: str, session_id: str):
        """Переводит аккаунт в режим сценария."""
        await self.account_manager.update_account_fields(
            char_id,
            {"state": "scenario", "scenario_session_id": session_id, "active_quest_key": quest_key},
        )

    async def clear_account_state(self, char_id: int):
        """Возвращает аккаунт в мир."""
        await self.account_manager.update_account_fields(
            char_id, {"state": "world", "scenario_session_id": "", "active_quest_key": ""}
        )

    async def backup_progress(self, char_id: int, quest_key: str, node_key: str, context: dict, session_id: uuid.UUID):
        """Сохраняет прогресс в БД (SQL)."""
        await self.repo.upsert_state(char_id, quest_key, node_key, context, session_id)

    async def delete_backup(self, char_id: int):
        """Удаляет запись о прогрессе из БД."""
        await self.repo.delete_state(char_id)

    async def get_backup(self, char_id: int) -> dict[str, Any] | None:
        """Прямое получение бэкапа из БД (для специфичных нужд)."""
        return await self.repo.get_active_state(char_id)

    async def get_session_id(self, char_id: int) -> str | None:
        """Получает ID текущей сессии из аккаунта."""
        return await self.account_manager.get_account_field(char_id, "scenario_session_id")
