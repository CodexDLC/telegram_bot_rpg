# database/repositories/ORM/leaderboard_repo.py
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_contract.i_leaderboard_repo import ILeaderboardRepo
from database.model_orm.leaderboard import Leaderboard


class LeaderboardRepoORM(ILeaderboardRepo):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_score(
        self, character_id: int, gear_score: int | None = None, xp: int | None = None, rating: int | None = None
    ) -> None:
        # Собираем только те поля, которые передали (не None)
        values = {}
        if gear_score is not None:
            values["gear_score"] = gear_score
        if xp is not None:
            values["total_xp"] = xp
        if rating is not None:
            values["pvp_rating"] = rating

        if not values:
            return

        # SQLite UPSERT: Пытаемся вставить, если конфликт (такой ID уже есть) -> обновляем
        stmt = sqlite_insert(Leaderboard).values(character_id=character_id, **values)
        stmt = stmt.on_conflict_do_update(index_elements=[Leaderboard.character_id], set_=values)
        await self.session.execute(stmt)
