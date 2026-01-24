# apps/game_core/modules/scenario_orchestrator/scenario_core_orchestrator.py
import uuid
from typing import TYPE_CHECKING, Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.core_response_dto import CoreResponseDTO, GameStateHeader
from apps.common.schemas_dto.game_state_enum import CoreDomain
from apps.common.schemas_dto.scenario_dto import ScenarioPayloadDTO
from backend.database.redis.redis_fields import AccountFields as Af
from backend.database.redis.redis_key import RedisKeys

# Импорт реестра хендлеров
from apps.game_core.modules.scenario_orchestrator.handlers.handler_registry import get_handler
from apps.game_core.modules.scenario_orchestrator.logic.scenario_director import ScenarioDirector
from apps.game_core.modules.scenario_orchestrator.logic.scenario_evaluator import ScenarioEvaluator
from apps.game_core.modules.scenario_orchestrator.logic.scenario_formatter import ScenarioFormatter
from apps.game_core.modules.scenario_orchestrator.logic.scenario_manager import ScenarioManager

if TYPE_CHECKING:
    pass


class ScenarioCoreOrchestrator:
    """
    Тонкий оркестратор.
    Отвечает только за координацию вызовов и формирование DTO.
    Вся логика переходов инкапсулирована в Director, а работа с данными в Manager.
    """

    def __init__(
        self,
        scenario_manager: ScenarioManager,
        scenario_evaluator: ScenarioEvaluator,
        scenario_director: ScenarioDirector,
        scenario_formatter: ScenarioFormatter,
        core_router: "SystemDispatcher | None" = None,
    ):
        self.manager = scenario_manager
        self.evaluator = scenario_evaluator
        self.director = scenario_director
        self.formatter = scenario_formatter
        self.core_router = core_router

    # --- Protocol Implementation ---

    async def get_entry_point(self, char_id: int, action: str, context: dict[str, Any]) -> Any:
        """
        Единая точка входа (CoreOrchestratorProtocol).
        """
        if action == "initialize":
            return await self.initialize_scenario_payload(
                char_id, context.get("quest_key", ""), context.get("prev_state"), context.get("prev_loc")
            )
        elif action == "resume":
            return await self.resume_scenario_payload(char_id)

        raise ValueError(f"Unknown action for Scenario: {action}")

    # --- Internal Logic (Returns Payload) ---

    async def initialize_scenario_payload(
        self, char_id: int, quest_key: str, prev_state: str | None = None, prev_loc: str | None = None
    ) -> ScenarioPayloadDTO:
        """Внутренняя логика инициализации (возвращает Payload)."""
        log.info(f"Orchestrator | action=init char={char_id} quest={quest_key}")

        quest_master = await self.manager.get_quest_master(quest_key)
        if not quest_master:
            raise ValueError(f"Quest {quest_key} not found")

        db_session = getattr(self.manager.repo, "session", None)
        if db_session is None:
            raise ValueError("Database session is not available in ScenarioManager repo")

        handler = get_handler(quest_key, self.manager, self.manager.account_manager, db_session)
        if not handler:
            raise ValueError(f"Scenario Handler for '{quest_key}' not found")

        # Генерируем session_id
        session_id = uuid.uuid4()
        quest_master["session_id"] = str(session_id)

        context = await handler.on_initialize(char_id, quest_master, prev_state, prev_loc)
        context["visited_nodes"] = []

        start_node_key = str(context.get("current_node_key"))
        node_data = await self.manager.get_node(quest_key, start_node_key)
        context["visited_nodes"].append(start_node_key)

        # Регистрируем состояние аккаунта
        await self.manager.update_account_state(char_id, quest_key, str(session_id))

        # Сохраняем в Redis
        await self.manager.save_session_context(char_id, context)

        # Бэкап
        await self.manager.backup_progress(char_id, quest_key, start_node_key, context, session_id)

        actions = self.director.get_available_actions(node_data.get("actions_logic", {}) if node_data else {}, context)
        dto = self.formatter.build_dto(node_data or {}, actions, context, quest_master)

        # Извлекаем payload из обертки ScenarioResponseDTO
        payload = dto.payload

        # ДОБАВЛЯЕМ CHAR_ID В EXTRA_DATA
        if payload.extra_data is None:
            payload.extra_data = {}
        payload.extra_data["char_id"] = char_id

        return payload

    async def resume_scenario_payload(self, char_id: int) -> ScenarioPayloadDTO:
        """Внутренняя логика восстановления (возвращает Payload)."""
        context = await self.manager.load_session(char_id)
        if not context:
            raise ValueError("No session found")

        quest_key = str(context.get("quest_key"))
        node_key = str(context.get("current_node_key"))

        node_data = await self.manager.get_node(quest_key, node_key)
        quest_master = await self.manager.get_quest_master(quest_key)

        actions = self.director.get_available_actions(node_data.get("actions_logic", {}) if node_data else {}, context)
        dto = self.formatter.build_dto(node_data or {}, actions, context, quest_master or {})

        payload = dto.payload

        # ДОБАВЛЯЕМ CHAR_ID
        if payload.extra_data is None:
            payload.extra_data = {}
        payload.extra_data["char_id"] = char_id

        return payload

    async def step_scenario_payload(self, char_id: int, action_id: str) -> ScenarioPayloadDTO | CoreResponseDTO:
        """
        Внутренняя логика шага.
        Может вернуть Payload (следующая сцена) или CoreResponseDTO (если произошла финализация и переход).
        """
        context = await self.manager.load_session(char_id)
        if not context:
            raise ValueError(f"Session for char {char_id} not found")

        quest_key = str(context.get("quest_key"))
        current_node_key = str(context.get("current_node_key"))

        # --- ПРОВЕРКА НА FINISH_QUEST ---
        current_node = await self.manager.get_node(quest_key, current_node_key)
        if current_node:
            action_data = current_node.get("actions_logic", {}).get(action_id, {})
            if action_data.get("type") == "finish_quest":
                # Завершаем квест и возвращаем результат перехода (CoreResponseDTO)
                return await self.finalize_scenario(char_id)
        # --------------------------------

        new_context, next_node_data = await self.director.execute_step(quest_key, current_node_key, action_id, context)

        new_context["current_node_key"] = next_node_data.get("node_key")
        new_context["total_steps"] = new_context.get("total_steps", 0) + 1

        if "visited_nodes" not in new_context:
            new_context["visited_nodes"] = []

        node_key = next_node_data.get("node_key")
        if node_key and node_key not in new_context["visited_nodes"]:
            new_context["visited_nodes"].append(node_key)

        await self.manager.save_session_context(char_id, new_context)

        if new_context["total_steps"] % 5 == 0 or next_node_data.get("force_backup"):
            await self._handle_backup(char_id, quest_key, str(new_context["current_node_key"]), new_context, None)

        quest_master = await self.manager.get_quest_master(quest_key)
        available_actions = self.director.get_available_actions(next_node_data.get("actions_logic", {}), new_context)

        dto = self.formatter.build_dto(next_node_data, available_actions, new_context, quest_master or {})

        payload = dto.payload

        # ДОБАВЛЯЕМ CHAR_ID
        if payload.extra_data is None:
            payload.extra_data = {}
        payload.extra_data["char_id"] = char_id

        return payload

    # --- Public API (Returns CoreResponseDTO) ---

    async def initialize_scenario(
        self, char_id: int, quest_key: str, prev_state: str | None = None, prev_loc: str | None = None
    ) -> CoreResponseDTO[ScenarioPayloadDTO]:
        payload = await self.initialize_scenario_payload(char_id, quest_key, prev_state, prev_loc)
        return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.SCENARIO), payload=payload)

    async def resume_scenario(self, char_id: int) -> CoreResponseDTO[ScenarioPayloadDTO]:
        payload = await self.resume_scenario_payload(char_id)
        return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.SCENARIO), payload=payload)

    async def step_scenario(self, char_id: int, action_id: str) -> CoreResponseDTO[ScenarioPayloadDTO]:
        result = await self.step_scenario_payload(char_id, action_id)

        # Если вернулся уже готовый CoreResponseDTO (из finalize), возвращаем его
        if isinstance(result, CoreResponseDTO):
            return result

        # Иначе оборачиваем payload
        return CoreResponseDTO(header=GameStateHeader(current_state=CoreDomain.SCENARIO), payload=result)

    async def finalize_scenario(self, char_id: int) -> CoreResponseDTO:
        """
        Завершение квеста.
        Делегирует логику перехода Хендлеру через SystemDispatcher.
        """
        # Берем контекст только из Redis. Если его нет - это ошибка логики.
        context = await self.manager.get_session_context(char_id)
        if not context:
            raise ValueError(f"Cannot finalize scenario: Session not found for char {char_id}")

        quest_key = str(context.get("quest_key", ""))
        db_session = getattr(self.manager.repo, "session", None)

        if db_session is None:
            raise ValueError("Database session is not available")

        handler = get_handler(quest_key, self.manager, self.manager.account_manager, db_session)
        if not handler:
            raise ValueError(f"Handler for {quest_key} not found")

        if not self.core_router:
            raise RuntimeError("SystemDispatcher is not initialized in ScenarioCoreOrchestrator")

        try:
            # 1. Логика хендлера (награды, статы, переход)
            # Хендлер сам вызывает router.get_initial_view и возвращает CoreResponseDTO
            response_dto = await handler.on_finalize(char_id, context, self.core_router)

            # 2. Очистка (делаем после успешной финализации)
            await self.manager.clear_account_state(char_id)
            await self.manager.clear_session(char_id)
            await self.manager.delete_backup(char_id)

            log.success(f"Orchestrator | char={char_id} quest completed")

            return response_dto

        except Exception as e:
            log.error(f"Orchestrator | finalize_failed char={char_id} error={e}")
            raise

    # --- Backup (Legacy/System) ---

    async def backup_session(self, char_id: int, db: AsyncSession) -> None:
        # (Код без изменений)
        context = await self.manager.get_session_context(char_id)
        if not context:
            return
        quest_key = context.get("quest_key")
        node_key = context.get("current_node_key")
        session_id_str = context.get("scenario_session_id")
        if not all([quest_key, node_key, session_id_str]):
            return
        session_id = uuid.UUID(str(session_id_str))
        await self.manager.repo.upsert_state(char_id, str(quest_key), str(node_key), context, session_id)
        await self.manager.redis.expire(RedisKeys.get_scenario_session_key(char_id), 3600)
        await self.manager.account_manager.delete_account_field(char_id, Af.SCENARIO_SESSION_ID)

    async def _handle_backup(self, char_id, quest_key, node_key, context, executor):
        # (Код без изменений)
        session_id_str = await self.manager.get_session_id(char_id)
        session_id = uuid.UUID(session_id_str) if session_id_str else uuid.uuid4()
        if executor and hasattr(executor, "add_task"):
            executor.add_task(self.manager.backup_progress, char_id, quest_key, node_key, context, session_id)
        else:
            await self.manager.backup_progress(char_id, quest_key, node_key, context, session_id)
