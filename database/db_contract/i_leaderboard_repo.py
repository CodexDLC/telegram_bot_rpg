# database/db_contract/i_leaderboard_repo.py
from abc import ABC, abstractmethod


class ILeaderboardRepo(ABC):
    @abstractmethod
    async def update_score(
        self, character_id: int, gear_score: int | None = None, xp: int | None = None, rating: int | None = None
    ) -> None:
        """Создает или обновляет запись в лидерборде."""
        pass
