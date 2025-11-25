from loguru import logger as log
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_contract.i_symbiote_repo import ISymbioteRepo
from database.model_orm.symbiote import CharacterSymbiote


class SymbioteRepoORM(ISymbioteRepo):
    """
    ORM-реализация репозитория Симбиота.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_symbiote(self, character_id: int) -> CharacterSymbiote | None:
        stmt = select(CharacterSymbiote).where(CharacterSymbiote.character_id == character_id)
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            log.exception(f"Ошибка при получении симбиота для char_id={character_id}: {e}")
            raise

    async def update_name(self, character_id: int, new_name: str) -> None:
        stmt = (
            update(CharacterSymbiote)
            .where(CharacterSymbiote.character_id == character_id)
            .values(symbiote_name=new_name)
        )
        try:
            await self.session.execute(stmt)
            log.debug(f"Имя симбиота для char_id={character_id} обновлено на '{new_name}'.")
        except SQLAlchemyError as e:
            log.exception(f"Ошибка при обновлении имени симбиота: {e}")
            raise

    async def set_gift(self, character_id: int, gift_id: str) -> None:
        stmt = update(CharacterSymbiote).where(CharacterSymbiote.character_id == character_id).values(gift_id=gift_id)
        try:
            await self.session.execute(stmt)
            log.info(f"Для char_id={character_id} установлен Дар: {gift_id}")
        except SQLAlchemyError as e:
            log.exception(f"Ошибка при установке Дара: {e}")
            raise

    async def update_progress(self, character_id: int, new_xp: int, new_rank: int) -> None:
        stmt = (
            update(CharacterSymbiote)
            .where(CharacterSymbiote.character_id == character_id)
            .values(gift_xp=new_xp, gift_rank=new_rank)
        )
        try:
            await self.session.execute(stmt)
            log.debug(f"Прогресс симбиота char_id={character_id} обновлен: XP={new_xp}, Rank={new_rank}")
        except SQLAlchemyError as e:
            log.exception(f"Ошибка при обновлении прогресса симбиота: {e}")
            raise
