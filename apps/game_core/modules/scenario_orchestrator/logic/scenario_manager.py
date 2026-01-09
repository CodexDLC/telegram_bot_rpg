# apps/game_core/modules/scenario_orchestrator/logic/scenario_manager.py
import json
import uuid
from typing import Any

from loguru import logger as log

from apps.common.database.db_contract.i_scenario_repo import IScenarioRepository
from apps.common.schemas_dto.game_state_enum import GameState
from apps.common.services.redis.manager.account_manager import AccountManager
from apps.common.services.redis.redis_fields import AccountFields as Af
from apps.common.services.redis.redis_key import RedisKeys
from apps.common.services.redis.redis_service import RedisService


class ScenarioManager:
    """
    Фасад данных.
    Централизованно управляет состоянием сессии (Redis + SQL Backup).
    Скрывает детали хранения от Оркестратора.
    """

    STATIC_TTL = 3600  # Время жизни кэша квеста (1 час)

    def __init__(self, redis_service: RedisService, repo: IScenarioRepository, account_manager: AccountManager):
        self.redis = redis_service
        self.repo = repo
        self.account_manager = account_manager

    # --- 1. Работа с сессией (User Session) ---

    async def register_new_session(self, char_id: int, quest_key: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Создает новую сессию: генерирует UUID, обновляет аккаунт и сохраняет контекст.
        """
        session_id = uuid.uuid4()
        session_id_str = str(session_id)

        # 1. Обновляем статус аккаунта
        await self.update_account_state(char_id, quest_key, session_id_str)

        # 2. Обогащаем контекст системными данными
        context[Af.SCENARIO_SESSION_ID] = session_id_str
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
        key = RedisKeys.get_scenario_session_key(char_id)
        raw_data = await self.redis.get_all_hash(key)
        if not raw_data:
            return {}

        context: dict[str, Any] = {}
        for k, v in raw_data.items():
            if v == "null":
                context[k] = None
                continue

            try:
                context[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
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
        key = RedisKeys.get_scenario_session_key(char_id)
        if not context:
            return

        processed_context = {}
        for k, v in context.items():
            if v is None:
                processed_context[k] = "null"
            elif isinstance(v, (dict, list, bool)):
                processed_context[k] = json.dumps(v, ensure_ascii=False)
            else:
                processed_context[k] = v

        await self.redis.set_hash_fields(key, processed_context)
        await self.redis.expire(key, ttl)

    async def clear_session(self, char_id: int):
        """Удаляет сессию из Redis."""
        key = RedisKeys.get_scenario_session_key(char_id)
        await self.redis.delete_key(key)

    # --- 2. Контент (Global Static Cache) ---

    async def _ensure_static_cache(self, quest_key: str) -> bool:
        """
        Проверяет наличие квеста в глобальном кэше Redis.
        Если нет — загружает ВСЁ из БД (Мастер + Ноды) и кэширует.
        """
        key = f"scenario:static:{quest_key}"
        if await self.redis.key_exists(key):
            return True

        log.info(f"Manager | Static Cache MISS for '{quest_key}'. Loading from DB...")

        # 1. Загружаем Мастер-данные
        master = await self.repo.get_master(quest_key)
        if not master:
            log.error(f"Manager | Quest '{quest_key}' not found in DB.")
            return False

        # 2. Загружаем ВСЕ ноды
        try:
            nodes = await self.repo.get_all_quest_nodes(quest_key)
        except AttributeError:
            log.error("Manager | Repo missing 'get_all_quest_nodes' method. Cannot cache quest.")
            return False

        # 3. Формируем Hash для Redis
        # Ключ 'master' -> JSON мастера
        # Ключ 'node:{id}' -> JSON ноды
        data = {
            "master": json.dumps(master, ensure_ascii=False, default=str),
        }

        count = 0
        for node in nodes:
            # Предполагаем, что node - это dict или объект, который можно сериализовать
            # И у него есть поле 'id' или 'key'
            n_id = node.get("node_key") or node.get("id")
            if n_id:
                data[f"node:{n_id}"] = json.dumps(node, ensure_ascii=False, default=str)
                count += 1

        # 4. Заливаем в Redis с TTL
        if data:
            await self.redis.set_hash_fields(key, data)
            await self.redis.expire(key, self.STATIC_TTL)
            log.success(f"Manager | Cached quest '{quest_key}': {count} nodes. TTL={self.STATIC_TTL}s")
            return True

        return False

    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        """
        Получает ноду. Сначала ищет в Redis Cache, затем фоллбэк в БД.
        """
        # 1. Пробуем кэш
        key = f"scenario:static:{quest_key}"
        cached_json = await self.redis.get_hash_field(key, f"node:{node_key}")

        if cached_json:
            try:
                return json.loads(cached_json)
            except json.JSONDecodeError:
                pass

        # 2. Если нет в кэше — пробуем загрузить весь квест
        if await self._ensure_static_cache(quest_key):
            # Повторная попытка из кэша
            cached_json = await self.redis.get_hash_field(key, f"node:{node_key}")
            if cached_json:
                return json.loads(cached_json)

        # 3. Фоллбэк: прямой запрос в БД (медленно)
        log.warning(f"Manager | Node miss in cache: {quest_key}/{node_key}. Fallback to DB.")
        return await self.repo.get_node(quest_key, node_key)

    async def get_quest_master(self, quest_key: str) -> dict[str, Any] | None:
        """
        Получает мастер-данные квеста. Сначала кэш, потом БД.
        """
        key = f"scenario:static:{quest_key}"
        cached_json = await self.redis.get_hash_field(key, "master")

        if cached_json:
            try:
                return json.loads(cached_json)
            except json.JSONDecodeError:
                pass

        if await self._ensure_static_cache(quest_key):
            cached_json = await self.redis.get_hash_field(key, "master")
            if cached_json:
                return json.loads(cached_json)

        return await self.repo.get_master(quest_key)

    async def get_nodes_by_pool(self, quest_key: str, pool_tag: str) -> list[dict[str, Any]]:
        """
        Получает список нод по тегу, используя Redis Cache.
        """
        # 1. Гарантируем наличие кэша
        if not await self._ensure_static_cache(quest_key):
            log.warning(f"Manager | Failed to cache quest '{quest_key}'. Fallback to DB.")
            return await self.repo.get_nodes_by_pool(quest_key, pool_tag)

        # 2. Загружаем все данные квеста из Redis
        key = f"scenario:static:{quest_key}"
        all_data = await self.redis.get_all_hash(key)

        candidates = []
        if all_data:
            for k, v in all_data.items():
                # Пропускаем мастер-запись и другие метаданные
                if not k.startswith("node:"):
                    continue

                try:
                    node_data = json.loads(v)
                    tags = node_data.get("tags")

                    # Проверяем наличие тега
                    if tags and isinstance(tags, list) and pool_tag in tags:
                        candidates.append(node_data)
                except (json.JSONDecodeError, TypeError):
                    continue

        return candidates

    # --- 3. Аккаунт и Бэкапы ---

    async def update_account_state(self, char_id: int, quest_key: str, session_id: str):
        """Переводит аккаунт в режим сценария."""
        await self.account_manager.update_account_fields(
            char_id,
            {Af.STATE: GameState.SCENARIO, Af.SCENARIO_SESSION_ID: session_id, Af.ACTIVE_QUEST_KEY: quest_key},
        )

    async def clear_account_state(self, char_id: int):
        """Возвращает аккаунт в мир."""
        await self.account_manager.update_account_fields(
            char_id, {Af.STATE: GameState.EXPLORATION, Af.SCENARIO_SESSION_ID: "", Af.ACTIVE_QUEST_KEY: ""}
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
        return await self.account_manager.get_account_field(char_id, Af.SCENARIO_SESSION_ID)
