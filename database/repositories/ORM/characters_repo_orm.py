# database/repositories/ORM/characters_repo_orm.py

import logging
from typing import Optional, List, Dict

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.character_dto import (
    CharacterStatsReadDTO, CharacterStatsUpdateDTO,
    CharacterReadDTO, CharacterShellCreateDTO, CharacterOnboardingUpdateDTO
)

from database.db_contract.i_characters_repo import ICharactersRepo, ICharacterStatsRepo

from database.model_orm.character import Characters, CharacterStats

log = logging.getLogger(__name__)


class CharactersRepoORM(ICharactersRepo):
    """
    Работа с Characters
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_character_shell(self, character_data: CharacterShellCreateDTO) -> int:
        """
        Создает "оболочку" персонажа (только user_id) и
        возвращает его новый character_id.
        """
        character_data_dict = character_data.model_dump()

        # noinspection PyArgumentList
        orm_character = Characters(**character_data_dict)
        orm_character.stats = CharacterStats()

        self.session.add(orm_character)
        log.debug(f"Выполнен Merge для Character: {orm_character.character_id}")

        await self.session.flush()
        log.debug(f"Выполнен flush для Character: {orm_character.character_id}")

        return orm_character.character_id


    async def update_character_onboarding(
            self,
            character_id: int,
            character_data: CharacterOnboardingUpdateDTO
    ) -> None:
        """
        Обновляет "оболочку" персонажа (имя, пол, game_stage)
        после прохождения создания.
        """

        stmt = (
            update(Characters)
            .where(Characters.character_id == character_id)
            .values(
                name=character_data.name,
                gender=character_data.gender,
                game_stage=character_data.game_stage
            )
        )
        await self.session.execute(stmt)
        log.debug(f"Данные персонажа {character_id} были обновлены на: {character_data}")


    async def get_character(self, character_id: int, **kwargs) -> Optional[CharacterReadDTO]:
        """
        Возвращает 'полную' DTO персонажа из БД.
        """
        stmt = select(Characters).where(Characters.character_id == character_id)

        result = await self.session.execute(stmt)
        orm_character = result.scalar_one_or_none()

        if orm_character:
            log.debug(f"Персонаж получен: {orm_character}")
            return CharacterReadDTO.model_validate(orm_character)
        return None

    async def get_characters(self, user_id: int, **kwargs) -> List[CharacterReadDTO]:
        """
        Возвращает список 'полных' DTO (для админки).
        """
        stmt = select(Characters).where(Characters.user_id == user_id)

        result = await self.session.scalars(stmt)
        orm_characters_list = result.all()

        if orm_characters_list:
            log.debug(f"Персонажи получены: {orm_characters_list}")
            return [CharacterReadDTO.model_validate(orm_character) for orm_character in orm_characters_list]
        return []

    async def delete_characters(self,character_id: int):
        """
        Удаляет персонажа.
        """
        stmt = delete(Characters).where(Characters.character_id == character_id)

        await self.session.execute(stmt)
        log.debug(f"Персонаж {character_id} был удален")

    async def update_character_game_stage(self, character_id: int, game_stage: str):
        """
        Обновляет стадию персонажа.
        """
        stmt = update(Characters).where(Characters.character_id == character_id).values(game_stage=game_stage)

        await self.session.execute(stmt)
        log.debug(f"Стадия персонажа {character_id} была обновлена на: {game_stage}")


class CharacterStatsRepoORM(ICharacterStatsRepo):

    def __init__(self, session: AsyncSession):
        self.session = session


    async def get_stats(self, character_id: int, **kwargs) -> CharacterStatsReadDTO | None:
        """
        Возвращает персонажа.
        """

        stmt = select(CharacterStats).where(CharacterStats.character_id == character_id)

        result = await self.session.execute(stmt)
        orm_stats = result.scalar_one_or_none()

        if orm_stats:
            log.debug(f"Статы получены: {orm_stats}")
            return CharacterStatsReadDTO.model_validate(orm_stats)
        return None




    async def update_stats(self,character_id: int, stats_data: CharacterStatsUpdateDTO):
        """
        Обновляет персонажа.
        """

        stmt = update(CharacterStats).where(CharacterStats.character_id == character_id).values(
            strength=stats_data.strength
            , agility=stats_data.agility
            , endurance=stats_data.endurance
            , charisma=stats_data.charisma
            , intelligence=stats_data.intelligence
            , perception=stats_data.perception
            , luck=stats_data.luck
        )

        await self.session.execute(stmt)
        log.debug(f"Stats персонажа {character_id} были обновлены")

    async def add_stats(self, character_id: int, stats_to_add: Dict[str, int]) -> Optional[CharacterStatsReadDTO]:
        """
        Атомарно добавляет значения к существующим статам И
        ВОЗВРАЩАЕТ обновленные данные. (Версия ORM)
        """

        if not stats_to_add:
            log.warning("Вызван add_stats с пустым словарем бонусов.")
            return None

        # 1. Белый список (как и у тебя)
        ALLOWED_STATS = {
            "strength", "agility", "endurance",
            "charisma", "intelligence", "perception", "luck"
        }

        # 2. Готовим словарь для .values()
        values_to_update = {}
        for stat, value in stats_to_add.items():
            if stat in ALLOWED_STATS:
                orm_column = getattr(CharacterStats, stat)
                values_to_update[stat] = orm_column + value

        if not values_to_update:
            log.warning("Вызван add_stats с пустым словарем бонусов.")
            return None

        # 3. Собираем АТОМАРНЫЙ UPDATE...
        stmt = (
            update(CharacterStats)
            .where(CharacterStats.character_id == character_id)
            .values(**values_to_update)
            .returning(CharacterStats)
        )

        # 4. Выполняем и получаем результат
        log.debug(f"Выполняем атомарный add_stats для {character_id}")
        result = await self.session.execute(stmt)
        orm_stats = result.scalar_one_or_none()
        if orm_stats:
            return CharacterStatsReadDTO.model_validate(orm_stats)
        return None


