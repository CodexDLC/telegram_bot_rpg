from sqlalchemy.ext.asyncio import AsyncSession

from app.services.core_service.manager.account_manager import AccountManager
from app.services.core_service.manager.arena_manager import ArenaManager
from app.services.core_service.manager.combat_manager import CombatManager
from app.services.game_service.arena.service_1v1 import Arena1v1Service


class ArenaService:
    """
    Фасад для всех механик Арены.

    Изолирует хэндлеры от конкретных реализаций режимов арены (1v1, Group, Tournament),
    предоставляя единый интерфейс для взаимодействия.
    """

    def __init__(
        self,
        session: AsyncSession,
        char_id: int,
        account_manager: AccountManager,
        arena_manager: ArenaManager,
        combat_manager: CombatManager,
    ):
        """
        Инициализирует ArenaService.

        Args:
            session: Асинхронная сессия базы данных.
            char_id: Уникальный идентификатор персонажа.
            account_manager: Менеджер аккаунтов.
            arena_manager: Менеджер арены.
            combat_manager: Менеджер боя.
        """
        self.session = session
        self.char_id = char_id
        self._service_1v1 = Arena1v1Service(session, char_id, arena_manager, combat_manager, account_manager)

    async def join_queue(self, mode: str) -> int | None:
        """
        Добавляет персонажа в очередь на арену для указанного режима.

        Args:
            mode: Режим арены (например, "1v1", "group").

        Returns:
            Gear Score персонажа, если успешно добавлен в очередь, иначе None.
        """
        if mode == "1v1":
            return await self._service_1v1.join_queue()
        # TODO: Добавить обработку других режимов арены (например, "group").
        return None

    async def check_match(self, mode: str, attempt: int) -> str | None:
        """
        Проверяет статус поиска матча для указанного режима.

        Используется для поллинга в UI.

        Args:
            mode: Режим арены.
            attempt: Номер текущей попытки проверки.

        Returns:
            Идентификатор боевой сессии, если матч найден, иначе None.
        """
        if mode == "1v1":
            return await self._service_1v1.check_and_match(attempt)
        # TODO: Добавить обработку других режимов арены.
        return None

    async def create_shadow_battle(self, mode: str) -> str:
        """
        Принудительно создает бой с "Тенью" (AI-противником) при таймауте поиска матча.

        Args:
            mode: Режим арены.

        Returns:
            Идентификатор созданной боевой сессии.
        """
        if mode == "1v1":
            return await self._service_1v1.create_shadow_battle()
        # TODO: Добавить обработку других режимов арены.
        return ""

    async def cancel_queue(self, mode: str) -> bool:
        """
        Отменяет поиск матча для указанного режима арены.

        Args:
            mode: Режим арены.

        Returns:
            True, если поиск успешно отменен, иначе False.
        """
        if mode == "1v1":
            await self._service_1v1.cancel_queue()
            return True
        # TODO: Добавить обработку других режимов арены.
        return False
