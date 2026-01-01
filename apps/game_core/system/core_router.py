from typing import TYPE_CHECKING, Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.session import get_async_session
from apps.common.schemas_dto.game_state_enum import CoreDomain

if TYPE_CHECKING:
    from apps.game_core.core_container import CoreContainer


class CoreRouter:
    """
    Маршрутизатор запросов между модулями (Core Layer).
    Позволяет одному оркестратору вызвать другой, а также обращаться к системным сервисам.
    Умеет управлять сессией БД (создавать временную, если не передана).
    """

    # Домены, которым ОБЯЗАТЕЛЬНО нужна сессия БД
    _DB_DOMAINS = {
        CoreDomain.CONTEXT_ASSEMBLER,
        CoreDomain.SCENARIO,
        CoreDomain.LOBBY,
        CoreDomain.ONBOARDING,
        CoreDomain.INVENTORY,
        CoreDomain.EXPLORATION,
        CoreDomain.COMBAT_INTERACTION,  # Может потребоваться для предметов
        # CoreDomain.COMBAT_ENTRY - теперь работает без сессии (Redis-bound)
    }

    def __init__(self, container: "CoreContainer"):
        self.container = container

    async def route(
        self,
        domain: str,
        action: str,
        context: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> Any:
        """
        Универсальный метод вызова домена/оркестратора.

        Args:
            domain: Имя домена (из CoreDomain).
            action: Действие (например, "initialize", "assemble").
            context: Данные запроса.
            session: Сессия БД. Если не передана, но нужна домену -> создается временная.
        """
        context = context or {}

        # 1. Определяем, нужна ли сессия
        needs_db = domain in self._DB_DOMAINS

        # 2. Если сессия есть -> используем её
        if session:
            return await self._execute_with_session(domain, action, context, session)

        # 3. Если сессии нет, но она нужна -> создаем временную
        if needs_db:
            async with get_async_session() as temp_session:
                return await self._execute_with_session(domain, action, context, temp_session)

        # 4. Если сессия не нужна -> вызываем без неё (передаем None)
        return await self._execute_with_session(domain, action, context, None)

    async def _execute_with_session(self, domain: str, action: str, context: dict, session: AsyncSession | None) -> Any:
        """Внутренний метод выполнения с разрешенной сессией."""
        orchestrator = self._get_orchestrator(domain, session)

        if not hasattr(orchestrator, "get_entry_point"):
            log.warning(f"CoreRouter | Orchestrator for {domain} does not implement get_entry_point")
            return None

        return await orchestrator.get_entry_point(action, context)

    def _get_orchestrator(self, domain: str, session: AsyncSession | None) -> Any:
        """
        Возвращает оркестратор для указанного домена.
        """
        # Игровые стейты (требуют сессию)
        if domain == CoreDomain.SCENARIO:
            if not session:
                raise ValueError(f"Session required for {domain}")
            return self.container.get_scenario_core_orchestrator(session)
        elif domain == CoreDomain.LOBBY:
            if not session:
                raise ValueError(f"Session required for {domain}")
            return self.container.get_lobby_core_orchestrator(session)
        elif domain == CoreDomain.ONBOARDING:
            if not session:
                raise ValueError(f"Session required for {domain}")
            return self.container.get_onboarding_core_orchestrator(session)
        elif domain == CoreDomain.INVENTORY:
            if not session:
                raise ValueError(f"Session required for {domain}")
            return self.container.get_inventory_core_orchestrator(session)
        elif domain == CoreDomain.EXPLORATION:
            if not session:
                raise ValueError(f"Session required for {domain}")
            return self.container.get_exploration_core_orchestrator(session)

        # Боевые домены
        elif domain == CoreDomain.COMBAT_ENTRY:
            return self.container.get_combat_entry_orchestrator()
        elif domain == CoreDomain.COMBAT_INTERACTION:
            return self.container.get_combat_interaction_orchestrator(session)
        # elif domain == CoreDomain.COMBAT:
        #     return self.container.get_combat_turn_orchestrator()

        # Системные сервисы
        elif domain == CoreDomain.CONTEXT_ASSEMBLER:
            if not session:
                raise ValueError(f"Session required for {domain}")
            return self.container.get_context_assembler(session)

        raise ValueError(f"Unknown domain for router: {domain}")

    # --- Legacy Aliases (для совместимости, если нужно) ---
    async def get_initial_view(
        self,
        target_state: str,
        session: AsyncSession,
        char_id: int | None = None,
        action: str = "initialize",
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Legacy wrapper for route."""
        context = context or {}
        if char_id is not None:
            context["char_id"] = char_id
        return await self.route(target_state, action, context, session)
