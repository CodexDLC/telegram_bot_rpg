import uuid
from typing import Any

from loguru import logger as log

from apps.common.database.db_contract.i_scenario_repo import IScenarioRepository
from apps.common.schemas_dto.scenario_dto import ScenarioResponseDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.game_service.quest.logic.scenario_director import ScenarioDirector
from apps.game_core.game_service.quest.logic.scenario_evaluator import ScenarioEvaluator
from apps.game_core.game_service.quest.logic.scenario_formatter import ScenarioFormatter
from apps.game_core.game_service.quest.logic.scenario_manager import ScenarioManager


class ScenarioCoreOrchestrator:
    """
    Главный оркестратор системы сценариев.
    Координирует работу саппорт-классов без жесткой привязки к фреймворку.
    """

    def __init__(
        self,
        repo: IScenarioRepository,
        account_manager: AccountManager,
        scenario_manager: ScenarioManager,
        scenario_evaluator: ScenarioEvaluator,
        scenario_director: ScenarioDirector,
        scenario_formatter: ScenarioFormatter,
    ):
        self.repo = repo
        self.account_manager = account_manager
        self.manager = scenario_manager
        self.evaluator = scenario_evaluator
        self.director = scenario_director
        self.formatter = scenario_formatter

    # --- 1. initialize_scenario (Старт) ---

    async def initialize_scenario(
        self, char_id: int, quest_key: str, prev_state: str | None = None, prev_loc: str | None = None
    ) -> ScenarioResponseDTO:
        """Запуск квеста: импорт данных из мира и создание первой сцены."""
        log.info(f"Orchestrator | action=init char={char_id} quest={quest_key}")

        quest_master = await self.repo.get_master(quest_key)
        if not quest_master:
            # В будущем можно вернуть DTO с ошибкой
            raise ValueError(f"Quest {quest_key} not found")

        # Генерация уникальной сессии
        session_id = uuid.uuid4()

        # Обновляем глобальный статус персонажа
        await self.account_manager.update_account_fields(
            char_id,
            {"state": "scenario", "scenario_session_id": str(session_id), "active_quest_key": quest_key},
        )

        # Импорт данных (Мир -> Песочница)
        init_instr = quest_master.get("init_sync", {})
        await self.manager.sync_external(char_id, init_instr, direction="import")

        # Подготовка контекста в Redis
        start_node_key = str(quest_master.get("start_node_id"))
        context = await self.manager.get_session_context(char_id)
        context.update(
            {
                "current_node_key": start_node_key,
                "step_counter": 0,
                "quest_key": quest_key,
                "prev_state": str(prev_state) if prev_state else None,
                "prev_loc": prev_loc,
            }
        )
        await self.manager.save_session_context(char_id, context)

        # Первичный бэкап в SQL
        await self.repo.upsert_state(char_id, quest_key, start_node_key, context, session_id)

        node_data = await self.repo.get_node(quest_key, start_node_key)
        if node_data is None:
            raise ValueError(f"Start node {start_node_key} not found for quest {quest_key}")

        actions = self.director.get_available_actions(node_data.get("actions_logic", {}), context)

        # Используем formatter для сборки DTO
        return self.formatter.build_dto(node_data, actions, context, quest_master)

    # --- 2. step_scenario (Ход) ---

    async def step_scenario(self, char_id: int, action_id: str, task_executor: Any = None) -> ScenarioResponseDTO:
        """
        Обработка действия.
        """
        context = await self.manager.get_session_context(char_id)
        if not context:
            raise ValueError("Session not found")

        quest_key = str(context.get("quest_key"))
        current_node_key = str(context.get("current_node_key"))

        node_data = await self.repo.get_node(quest_key, current_node_key)
        if node_data is None:
            raise ValueError(f"Node {current_node_key} not found for quest {quest_key}")

        quest_master = await self.repo.get_master(quest_key)
        if quest_master is None:
            raise ValueError(f"Quest master {quest_key} not found")

        # 1. Математика
        action_data = node_data.get("actions_logic", {}).get(action_id, {})
        context = self.evaluator.apply_math(action_data.get("math", {}), context)

        # 2. Навигация
        next_node_key = self.director.resolve_branching(action_data.get("branching", []), context)
        if next_node_key.startswith("pool:"):
            pool_tag = next_node_key.split(":")[1]
            candidates = await self.repo.get_nodes_by_pool(quest_key, pool_tag)
            next_node_key = str(self.director.select_node_from_pool(candidates, context))

        # 3. Сохранение в Redis
        context["current_node_key"] = next_node_key
        context["step_counter"] = context.get("step_counter", 0) + 1
        await self.manager.save_session_context(char_id, context)

        # 4. Бэкап в БД (Раз в 5 шагов)
        if context["step_counter"] % 5 == 0:
            await self._handle_backup(char_id, quest_key, next_node_key, context, task_executor)

        # 5. Сборка ответа
        next_node_data = await self.repo.get_node(quest_key, next_node_key)
        if next_node_data is None:
            raise ValueError(f"Next node {next_node_key} not found for quest {quest_key}")

        available_actions = self.director.get_available_actions(next_node_data.get("actions_logic", {}), context)

        return self.formatter.build_dto(next_node_data, available_actions, context, quest_master)

    # --- 3. resume_scenario (Восстановление) ---

    async def resume_scenario(self, char_id: int) -> ScenarioResponseDTO:
        """Восстанавливает сессию из БД, если Redis пуст."""
        log.info(f"Orchestrator | action=resume char={char_id}")

        context = await self.manager.get_session_context(char_id)

        if not context:
            db_state = await self.repo.get_active_state(char_id)
            if not db_state:
                raise ValueError("No session found in DB")

            context = db_state.get("context", {})
            await self.manager.save_session_context(char_id, context)

        quest_key = str(context.get("quest_key"))
        current_node_key = str(context.get("current_node_key"))

        node_data = await self.repo.get_node(quest_key, current_node_key)
        if node_data is None:
            raise ValueError(f"Node {current_node_key} not found for quest {quest_key}")

        quest_master = await self.repo.get_master(quest_key)
        if quest_master is None:
            raise ValueError(f"Quest master {quest_key} not found")

        actions = self.director.get_available_actions(node_data.get("actions_logic", {}), context)

        return self.formatter.build_dto(node_data, actions, context, quest_master)

    # --- 4. finalize_scenario (Завершение) ---

    async def finalize_scenario(self, char_id: int) -> dict[str, Any]:
        """Завершение квеста и экспорт данных."""
        context = await self.manager.get_session_context(char_id)
        quest_key = str(context.get("quest_key"))
        quest_master = await self.repo.get_master(quest_key)
        if quest_master is None:
            raise ValueError(f"Quest master {quest_key} not found")

        # Получаем данные для возврата
        prev_state = context.get("prev_state")
        prev_loc = context.get("prev_loc")

        # Экспорт (Песочница -> Мир)
        export_instr = quest_master.get("export_sync", {})
        await self.manager.sync_external(char_id, export_instr, direction="export")

        # Очистка
        await self.account_manager.update_account_fields(
            char_id, {"state": "world", "scenario_session_id": "", "active_quest_key": ""}
        )
        await self.manager.redis.delete_key(f"scen:session:{char_id}:data")
        await self.repo.delete_state(char_id)

        return {
            "status": "success",
            "message": "Export completed",
            "next_state": prev_state,
            "target_location_id": prev_loc,
        }

    # --- Вспомогательные методы ---

    async def _handle_backup(self, char_id, quest_key, node_key, context, executor):
        """Логика бэкапа с учетом будущей реализации FastAPI."""
        session_id_str = await self.account_manager.get_account_field(char_id, "scenario_session_id")
        session_id = uuid.UUID(session_id_str) if session_id_str else uuid.uuid4()

        if executor and hasattr(executor, "add_task"):
            executor.add_task(self.repo.upsert_state, char_id, quest_key, node_key, context, session_id)
        else:
            await self.repo.upsert_state(char_id, quest_key, node_key, context, session_id)
