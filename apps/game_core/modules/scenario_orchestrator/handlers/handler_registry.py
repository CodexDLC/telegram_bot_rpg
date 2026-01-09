# apps/game_core/modules/scenario_orchestrator/handlers/handler_registry.py

from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.services.redis.manager.account_manager import AccountManager
from apps.game_core.modules.scenario_orchestrator.logic.scenario_manager import ScenarioManager

from .base_handler import BaseScenarioHandler
from .tutorial_handler import TutorialScenarioHandler

# Словарь специфичных обработчиков
_HANDLERS: dict[str, type[BaseScenarioHandler]] = {
    "awakening_rift": TutorialScenarioHandler,
    # Сюда добавлять новые квесты
}


def get_handler(
    quest_key: str, scenario_manager: ScenarioManager, account_manager: AccountManager, db_session: AsyncSession
) -> BaseScenarioHandler | None:
    """
    Фабричный метод.
    Возвращает специфичный обработчик для сценария.
    Если обработчик не найден, возвращает None (что приведет к ошибке в Оркестраторе).
    """
    handler_class = _HANDLERS.get(quest_key)

    if not handler_class:
        return None

    # Инъекция зависимостей
    return handler_class(scenario_manager, account_manager, db_session)
