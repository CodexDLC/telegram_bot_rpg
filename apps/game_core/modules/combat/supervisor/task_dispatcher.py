from typing import Protocol

from loguru import logger as log

from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.game_core.modules.combat.supervisor.combat_supervisor_manager import (
    add_supervisor_task,
    get_supervisor_task,
)


class CombatTaskDispatcherProtocol(Protocol):
    """
    Интерфейс для запуска фоновых задач боя (Supervisor/Worker).
    Позволяет подменять реализацию (Local Asyncio vs ARQ) без изменения бизнес-логики.
    """

    async def dispatch_check(self, session_id: str) -> None:
        """
        Запускает задачу проверки состояния боя (мгновенная реакция).
        """
        ...


class LocalAsyncioDispatcher:
    """
    Реализация диспетчера на базе локальных asyncio.Task.
    Использует CombatSupervisorManager для отслеживания запущенных задач.
    """

    def __init__(self, combat_manager: CombatManager, account_manager: AccountManager):
        self.combat_manager = combat_manager
        self.account_manager = account_manager

    async def dispatch_check(self, session_id: str) -> None:
        """
        Проверяет, запущен ли локальный супервизор. Если нет — запускает.
        """
        if get_supervisor_task(session_id):
            # Супервизор уже работает, ничего делать не надо.
            # В модели Stateful Supervisor он сам крутит цикл.
            return

        # Избегаем циклических импортов (Supervisor импортирует Manager, Manager импортирует Dispatcher...)
        # Импорт внутри метода — нормальная практика для таких случаев.
        import asyncio

        from apps.game_core.modules.combat.supervisor.combat_supervisor import CombatSupervisor

        log.info(f"LocalDispatcher | Starting supervisor for {session_id}")

        # Создаем экземпляр супервизора
        supervisor = CombatSupervisor(session_id, self.combat_manager, self.account_manager)

        # Запускаем его run() как фоновую задачу
        task = asyncio.create_task(supervisor.run())

        # Регистрируем в менеджере (чтобы не запустить второй раз)
        add_supervisor_task(session_id, task)
