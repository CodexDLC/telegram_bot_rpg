from collections.abc import Callable
from typing import Any

from loguru import logger as log

# Тип фабрики: теперь не принимает сессию, так как оркестраторы автономны
OrchestratorFactory = Callable[[], Any]


class SystemDispatcher:
    """
    Маршрутизатор запросов между модулями (Core Layer).
    Реализует паттерн Registry: домены регистрируются извне.

    Stateless: Не управляет сессиями БД.
    """

    def __init__(self):
        # Реестр фабрик: { "domain_name": factory_func }
        self._registry: dict[str, OrchestratorFactory] = {}

    def register(self, domain: str, factory: OrchestratorFactory) -> None:
        """
        Регистрация обработчика для домена.
        """
        self._registry[domain] = factory
        log.debug(f"SystemDispatcher | Registered domain: {domain}")

    async def route(
        self,
        domain: str,
        action: str,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """
        Универсальный метод вызова домена/оркестратора.
        """
        context = context or {}

        # 1. Ищем фабрику
        factory = self._registry.get(domain)
        if not factory:
            log.error(f"SystemDispatcher | Domain '{domain}' not registered")
            raise ValueError(f"Unknown domain for router: {domain}")

        # 2. Выполняем
        return await self._execute(factory, action, context)

    async def _execute(self, factory: OrchestratorFactory, action: str, context: dict) -> Any:
        """Внутренний метод выполнения."""
        # Создаем/получаем оркестратор через фабрику
        orchestrator = factory()

        if not hasattr(orchestrator, "get_entry_point"):
            log.warning("SystemDispatcher | Orchestrator for domain does not implement get_entry_point")
            return None

        return await orchestrator.get_entry_point(action, context)
