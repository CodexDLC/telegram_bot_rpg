#database/repositories/ORM/modifiers_repo.py
from loguru import logger as log
from typing import Optional, Dict, Any

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.modifer_dto import CharacterModifiersDTO, CharacterModifiersSaveDto
from database.db_contract.i_modifiers_repo import ICharacterModifiersRepo
from database.model_orm import CharacterModifiers


class CharacterModifiersRepo(ICharacterModifiersRepo):

    def __init__(self, session: AsyncSession):
        self.session = session


    async def get_modifiers(self, character_id: int) -> Optional[CharacterModifiersDTO]:
        """
        Получает ВСЕ модификаторы (DTO для чтения) для одного персонажа.
        """
        log.debug(f"Запрос на получение модификаторов для character_id={character_id}")
        stmt = select(CharacterModifiers).where(CharacterModifiers.character_id == character_id)
        try:
            result = await self.session.execute(stmt)
            orm_modifiers = result.scalar_one_or_none()

            if orm_modifiers:
                log.debug(f"Модификаторы для character_id={character_id} найдены.")
                return CharacterModifiersDTO.model_validate(orm_modifiers)
            log.debug(f"Модификаторы для character_id={character_id} не найдены.")
            return None
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при получении модификаторов для character_id={character_id}: {e}")
            raise




    async def save_modifiers(self, character_id: int, data: CharacterModifiersSaveDto) -> None:
        """
        Полностью перезаписывает (UPDATE) все модификаторы персонажа,
        используя DTO для сохранения.
        """
        log.debug(f"Запрос на полное обновление модификаторов для character_id={character_id}")
        stmt = (
            update(CharacterModifiers)
            .where(CharacterModifiers.character_id == character_id)
            .values(**data.model_dump())
        )
        try:
            await self.session.execute(stmt)
            log.debug(f"Модификаторы персонажа {character_id} были успешно обновлены.")
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при обновлении модификаторов для character_id={character_id}: {e}")
            raise


    async def update_specific_modifiers(self, character_id: int, updates: Dict[str, Any]) -> None:
        """
        Частично обновляет (UPDATE) только указанные поля в модификаторах.
        Пример: updates = {"armor_head": "2d6", "hp_max": 150}
        """
        log.debug(f"Запрос на частичное обновление модификаторов для character_id={character_id}")

        stmt = (
            update(CharacterModifiers)
            .where(CharacterModifiers.character_id == character_id)
            .values(**updates)
        )

        try:
            await self.session.execute(stmt)
            log.debug(f"Модификаторы персонажа {character_id} были успешно частично обновлены.")
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при частичном обновлении модификаторов для character_id={character_id}: {e}")
            raise

