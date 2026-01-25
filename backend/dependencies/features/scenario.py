from typing import Annotated

from fastapi import Depends

from backend.database.postgres.repositories.scenario_repository import ScenarioRepositoryORM
from backend.dependencies.base import DbSessionDep, RedisContainerDep
from backend.domains.user_features.scenario.engine.director import ScenarioDirector
from backend.domains.user_features.scenario.engine.evaluator import ScenarioEvaluator
from backend.domains.user_features.scenario.engine.formatter import ScenarioFormatter
from backend.domains.user_features.scenario.gateway.scenario_gateway import ScenarioGateway
from backend.domains.user_features.scenario.service.scenario_service import ScenarioService
from backend.domains.user_features.scenario.service.session_service import ScenarioSessionService

# --- 1. Domain Services ---


async def get_scenario_session_service(container: RedisContainerDep, db: DbSessionDep) -> ScenarioSessionService:
    """
    Factory for ScenarioSessionService.
    Uses RedisContainer to access ScenarioManager and AccountManager.
    """
    repo = ScenarioRepositoryORM(db)
    return ScenarioSessionService(scenario_manager=container.scenario, account_manager=container.account, repo=repo)


ScenarioSessionServiceDep = Annotated[ScenarioSessionService, Depends(get_scenario_session_service)]


# --- 2. Engine Components ---


async def get_scenario_evaluator() -> ScenarioEvaluator:
    return ScenarioEvaluator()


ScenarioEvaluatorDep = Annotated[ScenarioEvaluator, Depends(get_scenario_evaluator)]


async def get_scenario_formatter() -> ScenarioFormatter:
    return ScenarioFormatter()


ScenarioFormatterDep = Annotated[ScenarioFormatter, Depends(get_scenario_formatter)]


async def get_scenario_director(
    evaluator: ScenarioEvaluatorDep, session_service: ScenarioSessionServiceDep
) -> ScenarioDirector:
    return ScenarioDirector(evaluator, session_service)


ScenarioDirectorDep = Annotated[ScenarioDirector, Depends(get_scenario_director)]


# --- 3. Main Service ---


async def get_scenario_service(
    session_service: ScenarioSessionServiceDep,
    evaluator: ScenarioEvaluatorDep,
    director: ScenarioDirectorDep,
    formatter: ScenarioFormatterDep,
    # TODO: Add SystemDispatcherDep when available
) -> ScenarioService:
    return ScenarioService(session_service, evaluator, director, formatter, core_router=None)


ScenarioServiceDep = Annotated[ScenarioService, Depends(get_scenario_service)]


# --- 4. Gateway ---


async def get_scenario_gateway(service: ScenarioServiceDep) -> ScenarioGateway:
    return ScenarioGateway(service)


ScenarioGatewayDep = Annotated[ScenarioGateway, Depends(get_scenario_gateway)]
