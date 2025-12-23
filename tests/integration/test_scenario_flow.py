import pytest

from apps.common.database.repositories.ORM.characters_repo_orm import CharactersRepoORM
from apps.common.database.repositories.ORM.scenario_repository import ScenarioRepositoryORM
from apps.common.database.repositories.ORM.users_repo_orm import UsersRepoORM
from apps.common.schemas_dto.character_dto import CharacterShellCreateDTO
from apps.common.schemas_dto.user_dto import UserUpsertDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.game_core.game_service.scenario_orchestrator.logic.scenario_director import ScenarioDirector
from apps.game_core.game_service.scenario_orchestrator.logic.scenario_evaluator import ScenarioEvaluator
from apps.game_core.game_service.scenario_orchestrator.logic.scenario_formatter import ScenarioFormatter
from apps.game_core.game_service.scenario_orchestrator.logic.scenario_manager import ScenarioManager
from apps.game_core.game_service.scenario_orchestrator.scenario_core_orchestrator import ScenarioCoreOrchestrator
from apps.game_core.utils.scenario_loader import ScenarioLoader


@pytest.fixture
async def scenario_env(get_async_session, app_container):
    """
    Готовит окружение: загружает сценарии, создает юзера и оркестратор.
    """
    async_session_factory = get_async_session
    redis_service = app_container.redis_service

    async with async_session_factory() as db_session:
        # 1. Загрузка сценариев
        loader = ScenarioLoader(db_session)
        await loader.load_all_scenarios()

        # 2. Создание юзера и персонажа
        user_repo = UsersRepoORM(db_session)
        char_repo = CharactersRepoORM(db_session)
        tg_id = 123456789

        user = await user_repo.get_user(tg_id)
        if not user:
            user_dto = UserUpsertDTO(
                telegram_id=tg_id,
                first_name="Test",
                last_name=None,
                username="TestUser",
                is_premium=False,
                language_code="en",
            )
            await user_repo.upsert_user(user_dto)

        # Исправлено: убраны лишние аргументы name и gender, так как CharacterShellCreateDTO их не принимает
        char_id = await char_repo.create_character_shell(CharacterShellCreateDTO(user_id=tg_id))

        # ВАЖНО: Коммитим создание персонажа, чтобы он был доступен для FK проверок в других транзакциях (если они будут)
        # Или просто чтобы зафиксировать состояние перед тестом.
        await db_session.commit()

        # 3. Сборка оркестратора
        scenario_repo = ScenarioRepositoryORM(db_session)
        account_manager = AccountManager(redis_service)
        manager = ScenarioManager(redis_service, scenario_repo, account_manager)
        evaluator = ScenarioEvaluator(seed=42)
        director = ScenarioDirector(evaluator, manager)
        formatter = ScenarioFormatter()
        orchestrator = ScenarioCoreOrchestrator(manager, evaluator, director, formatter)

        return {"char_id": char_id, "orchestrator": orchestrator, "manager": manager, "db_session": db_session}


@pytest.mark.asyncio
async def test_full_scenario_flow(scenario_env):
    """
    Проверяет полный цикл работы движка на примере Туториала.
    """
    # Убрали await, так как фикстура уже разрезолвлена pytest-ом
    env = scenario_env

    char_id = env["char_id"]
    orchestrator = env["orchestrator"]
    manager = env["manager"]
    quest_key = "awakening_rift"

    # 1. Инициализация (Handler.on_initialize)
    response = await orchestrator.initialize_scenario(char_id, quest_key)
    assert response.status == "success"
    assert response.payload.node_key == "rift_entry_01"

    # Проверка контекста
    context = await manager.get_session_context(char_id)
    assert context["quest_key"] == quest_key
    assert context["w_strength"] == 0

    # 2. Шаг 1: Простая математика (w_wisdom + 1)
    response = await orchestrator.step_scenario(char_id, "next")
    assert response.payload.node_key == "crash_sequence_02"

    context = await manager.get_session_context(char_id)
    assert context["w_wisdom"] == 1

    # 3. Шаг 2: Прыжок в пул (Smart Selection)
    response = await orchestrator.step_scenario(char_id, "fall")
    assert "bridge_early" in response.payload.node_key

    # 4. Финализация (Handler.on_finalize)
    # Накручиваем статы для проверки наград
    context["w_strength"] = 20
    context["loot_queue"] = ["sword_test"]
    await manager.save_session_context(char_id, context)

    result = await orchestrator.finalize_scenario(char_id)
    assert result["status"] == "success"

    # Проверка очистки
    context_after = await manager.get_session_context(char_id)
    assert context_after == {}
