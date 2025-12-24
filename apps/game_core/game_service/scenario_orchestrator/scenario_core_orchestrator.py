# apps/game_core/game_service/scenario_orchestrator/scenario_core_orchestrator.py
import uuid
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.scenario_dto import ScenarioResponseDTO

# Импорт реестра хендлеров
from apps.game_core.game_service.scenario_orchestrator.handlers.handler_registry import get_handler
from apps.game_core.game_service.scenario_orchestrator.logic.scenario_director import ScenarioDirector
from apps.game_core.game_service.scenario_orchestrator.logic.scenario_evaluator import ScenarioEvaluator
from apps.game_core.game_service.scenario_orchestrator.logic.scenario_formatter import ScenarioFormatter
from apps.game_core.game_service.scenario_orchestrator.logic.scenario_manager import ScenarioManager


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
    ):
        self.manager = scenario_manager
        self.evaluator = scenario_evaluator
        self.director = scenario_director
        self.formatter = scenario_formatter

    # --- 1. initialize_scenario (Старт) ---

    async def initialize_scenario(
        self, char_id: int, quest_key: str, prev_state: str | None = None, prev_loc: str | None = None
    ) -> ScenarioResponseDTO:
        """Запуск сценария через Handler."""
        log.info(f"Orchestrator | action=init char={char_id} quest={quest_key}")

        quest_master = await self.manager.get_quest_master(quest_key)
        if not quest_master:
            raise ValueError(f"Quest {quest_key} not found")

        # Получаем сессию БД через репозиторий менеджера
        db_session = getattr(self.manager.repo, "session", None)
        if not isinstance(db_session, AsyncSession):
            # Если сессии нет или она не того типа, это проблема конфигурации
            # Но для тестов или моков может быть None.
            # Попробуем обработать это, но get_handler требует AsyncSession.
            # Если repo это ORM репозиторий, у него есть session.
            pass

        # Фабрика хендлеров
        # Мы предполагаем, что db_session валидна, если нет - get_handler может упасть или вернуть None
        # Mypy ругается на Any | None, поэтому явно кастим или проверяем
        if db_session is None:
            raise ValueError("Database session is not available in ScenarioManager repo")

        handler = get_handler(quest_key, self.manager, self.manager.account_manager, db_session)
        if not handler:
            raise ValueError(f"Scenario Handler for '{quest_key}' not found")

        # Хендлер создает начальный контекст и регистрирует сессию
        context = await handler.on_initialize(char_id, quest_master, prev_state, prev_loc)

        # Получаем данные стартовой ноды
        start_node_key = str(context.get("current_node_key"))
        node_data = await self.manager.get_node(quest_key, start_node_key)

        # Первичный бэкап (теперь обязателен при старте)
        session_id_str = str(context.get("scenario_session_id"))
        session_id = uuid.UUID(session_id_str) if session_id_str else uuid.uuid4()
        await self.manager.backup_progress(char_id, quest_key, start_node_key, context, session_id)

        # Сборка DTO
        actions = self.director.get_available_actions(node_data.get("actions_logic", {}) if node_data else {}, context)
        return self.formatter.build_dto(node_data or {}, actions, context, quest_master)

    # --- 2. step_scenario (Ход) ---

    async def step_scenario(self, char_id: int, action_id: str, task_executor: Any = None) -> ScenarioResponseDTO:
        """Обработка действия игрока."""
        # Умная загрузка: если Redis пуст, подтянет из БД
        context = await self.manager.load_session(char_id)
        if not context:
            raise ValueError(f"Session for char {char_id} not found and cannot be restored")

        quest_key = str(context.get("quest_key"))
        current_node_key = str(context.get("current_node_key"))

        # Директор исполняет всю логику: Math -> Branching -> Logic Gates
        new_context, next_node_data = await self.director.execute_step(quest_key, current_node_key, action_id, context)

        # Сохранение прогресса
        new_context["current_node_key"] = next_node_data.get("node_key")
        new_context["step_counter"] = new_context.get("step_counter", 0) + 1
        await self.manager.save_session_context(char_id, new_context)

        # Бэкап в БД (Раз в 5 шагов или по флагу из ноды)
        if new_context["step_counter"] % 5 == 0 or next_node_data.get("force_backup"):
            await self._handle_backup(
                char_id, quest_key, str(new_context["current_node_key"]), new_context, task_executor
            )

        # Сборка DTO
        quest_master = await self.manager.get_quest_master(quest_key)
        available_actions = self.director.get_available_actions(next_node_data.get("actions_logic", {}), new_context)

        return self.formatter.build_dto(next_node_data, available_actions, new_context, quest_master or {})

    # --- 3. resume_scenario (Восстановление) ---

    async def resume_scenario(self, char_id: int) -> ScenarioResponseDTO:
        """Просто пересобирает DTO текущего состояния."""
        context = await self.manager.load_session(char_id)
        if not context:
            raise ValueError("No session found")

        quest_key = str(context.get("quest_key"))
        node_key = str(context.get("current_node_key"))

        node_data = await self.manager.get_node(quest_key, node_key)
        quest_master = await self.manager.get_quest_master(quest_key)

        actions = self.director.get_available_actions(node_data.get("actions_logic", {}) if node_data else {}, context)
        return self.formatter.build_dto(node_data or {}, actions, context, quest_master or {})

    # --- 4. finalize_scenario (Завершение) ---

    async def finalize_scenario(self, char_id: int) -> dict[str, Any]:
        """Завершение квеста через экспорт в Handler."""
        context = await self.manager.get_session_context(char_id)
        if not context:
            # Если в Redis пусто, пробуем достать из БД последний бэкап для финализации
            db_state = await self.manager.get_backup(char_id)
            context = db_state.get("context", {}) if db_state else {}

        quest_key = str(context.get("quest_key", ""))

        db_session = getattr(self.manager.repo, "session", None)
        if db_session is None:
            raise ValueError("Database session is not available in ScenarioManager repo")

        handler = get_handler(quest_key, self.manager, self.manager.account_manager, db_session)
        if not handler:
            raise ValueError(f"Handler for {quest_key} not found for finalization")

        try:
            # 1. Логика выдачи наград и статов (внутри хендлера)
            await handler.on_finalize(char_id, context)

            # 2. Очистка временных данных
            await self.manager.clear_account_state(char_id)
            await self.manager.clear_session(char_id)
            await self.manager.delete_backup(char_id)

            log.success(f"Orchestrator | char={char_id} quest completed and cleaned")

        except Exception as e:
            log.error(f"Orchestrator | finalize_failed char={char_id} error={e}")
            raise

        return {
            "status": "success",
            "message": "Scenario finalized",
            "next_state": context.get("prev_state", "world"),
            "target_location_id": context.get("prev_loc"),
        }

    async def backup_session(self, char_id: int, db: AsyncSession) -> None:
        """
        Реализация метода для SessionSyncDispatcher.
        Собирает контекст из Redis и делает холодный бэкап в Postgres.
        """
        # 1. Загружаем текущий контекст из Redis через менеджер
        context = await self.manager.get_session_context(char_id)
        if not context:
            log.warning(f"Scenario | No session to backup for {char_id}")
            return

        # 2. Вытаскиваем метаданные для репозитория
        quest_key = context.get("quest_key")
        node_key = context.get("current_node_key")
        session_id_str = context.get("scenario_session_id")

        if not all([quest_key, node_key, session_id_str]):
            log.error(f"Scenario | Incomplete context for backup: {char_id}")
            return

        session_id = uuid.UUID(str(session_id_str))

        # 3. Делаем холодный бэкап в БД (IScenarioRepository)
        # Передаем session напрямую, так как мы в FastAPI контексте
        # Mypy fix: ensure quest_key and node_key are strings
        await self.manager.repo.upsert_state(char_id, str(quest_key), str(node_key), context, session_id)

        # 4. СТАВИМ TTL (Теплая сессия)
        # Оставляем данные в Redis на 1 час, чтобы игрок мог вернуться
        await self.manager.redis.expire(f"scen:session:{char_id}:data", 3600)

        # 5. ОТЦЕПЛЯЕМ СЕССИЮ ОТ ЯДРА
        # Удаляем только ссылку, чтобы Диспетчер больше не считал эту сессию активной
        await self.manager.account_manager.delete_account_field(char_id, "scenario_session_id")

        log.info(f"Scenario | Session backed up and unlinked for {char_id}")

    # --- Вспомогательные методы ---

    async def _handle_backup(self, char_id, quest_key, node_key, context, executor):
        session_id_str = await self.manager.get_session_id(char_id)
        session_id = uuid.UUID(session_id_str) if session_id_str else uuid.uuid4()

        if executor and hasattr(executor, "add_task"):
            executor.add_task(self.manager.backup_progress, char_id, quest_key, node_key, context, session_id)
        else:
            await self.manager.backup_progress(char_id, quest_key, node_key, context, session_id)
