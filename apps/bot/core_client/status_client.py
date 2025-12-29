from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.schemas_dto.status_dto import FullCharacterDataDTO
from apps.game_core.modules.status.status_orchestrator import StatusCoreOrchestrator


class StatusClient:
    """
    Клиент для взаимодействия с системой статуса персонажа.
    """

    def __init__(self, session: AsyncSession):
        self._orchestrator = StatusCoreOrchestrator(session)

    async def get_full_data(self, char_id: int) -> FullCharacterDataDTO | None:
        return await self._orchestrator.get_full_character_data(char_id)

    async def update_skill_state(self, char_id: int, skill_key: str, state: str) -> bool:
        """Обновляет режим прокачки навыка."""
        # TODO: Реализовать в StatusCoreOrchestrator метод update_skill_state
        # return await self._orchestrator.update_skill_state(char_id, skill_key, state)
        return True  # Заглушка
