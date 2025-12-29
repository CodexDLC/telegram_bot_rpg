from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.game.arena_dto import ArenaMatchResponse, ArenaQueueResponse
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.arena_manager import ArenaManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.game_core.modules.arena.arena_orchestrator import ArenaCoreOrchestrator


class ArenaClient:
    """
    Клиент для взаимодействия с логикой Арены.
    В текущей реализации (монолит) он напрямую вызывает ArenaCoreOrchestrator.
    В будущем (микросервисы) здесь будут REST API вызовы.
    """

    def __init__(
        self,
        session: AsyncSession,
        account_manager: AccountManager,
        arena_manager: ArenaManager,
        combat_manager: CombatManager,
    ):
        # В будущем __init__ будет принимать http_client, а не все менеджеры
        self._orchestrator = ArenaCoreOrchestrator(session, account_manager, arena_manager, combat_manager)

    async def toggle_queue(self, mode: str, char_id: int) -> ArenaQueueResponse:
        """
        Запрашивает постановку или снятие с очереди.
        """
        # Сейчас: прямой вызов
        return await self._orchestrator.process_toggle_queue(mode, char_id)

        # В будущем:
        # response = await self._http_client.post(
        #     "/arena/queue/toggle", json={"mode": mode, "char_id": char_id}
        # )
        # return ArenaQueueResponse(**response.json())

    async def check_match(self, mode: str, char_id: int) -> ArenaMatchResponse:
        """
        Запрашивает проверку статуса матча.
        """
        # Сейчас: прямой вызов
        return await self._orchestrator.process_check_match(mode, char_id)

        # В будущем:
        # response = await self._http_client.get(
        #     f"/arena/match/status?mode={mode}&char_id={char_id}"
        # )
        # return ArenaMatchResponse(**response.json())
