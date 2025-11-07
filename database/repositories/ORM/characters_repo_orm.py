# database/repositories/ORM/characters_repo_orm.py
import logging
from typing import Optional, List, Dict

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.resources.schemas_dto.character_dto import (
    CharacterStatsReadDTO, CharacterStatsUpdateDTO,
    CharacterReadDTO, CharacterShellCreateDTO, CharacterOnboardingUpdateDTO
)
from database.db_contract.i_characters_repo import ICharactersRepo, ICharacterStatsRepo
from database.model_orm.character import Character, CharacterStats

log = logging.getLogger(__name__)


class CharactersRepoORM(ICharactersRepo):
    """
    ORM-реализация репозитория для управления основными данными персонажей.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug(f"Инициализирован {self.__class__.__name__} с сессией: {session}")

    async def create_character_shell(self, character_data: CharacterShellCreateDTO) -> int:
        """
        Создает "оболочку" персонажа и связанные с ней статы.

        Создает экземпляр `Character` и `CharacterStats`, добавляет их в сессию
        и использует `flush` для получения `character_id` до коммита.
        """
        character_data_dict = character_data.model_dump()
        log.debug(f"Создание 'оболочки' персонажа для user_id={character_data.user_id}")

        try:
            # noinspection PyArgumentList
            orm_character = Character(**character_data_dict)
            # SQLAlchemy автоматически создаст CharacterStats из-за cascade
            # orm_character.stats = CharacterStats()

            self.session.add(orm_character)
            # flush() отправляет изменения в БД и синхронизирует ID,
            # но не коммитит транзакцию.
            await self.session.flush()
            log.debug(f"Выполнен flush для Character, получен character_id: {orm_character.character_id}")

            return orm_character.character_id
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при создании 'оболочки' персонажа: {e}")
            raise

    async def update_character_onboarding(
            self,
            character_id: int,
            character_data: CharacterOnboardingUpdateDTO
    ) -> None:
        """Обновляет данные персонажа после онбординга (имя, пол, стадия)."""
        log.debug(f"Обновление данных онбординга для character_id={character_id} на: {character_data.model_dump_json()}")
        stmt = (
            update(Character)
            .where(Character.character_id == character_id)
            .values(**character_data.model_dump())
        )
        try:
            await self.session.execute(stmt)
            log.debug(f"Данные персонажа {character_id} были успешно обновлены.")
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при обновлении данных онбординга для character_id={character_id}: {e}")
            raise

    async def get_character(self, character_id: int, **kwargs) -> Optional[CharacterReadDTO]:
        """Возвращает DTO персонажа по его ID."""
        log.debug(f"Запрос на получение персонажа по character_id={character_id}")
        stmt = select(Character).where(Character.character_id == character_id)
        try:
            result = await self.session.execute(stmt)
            orm_character = result.scalar_one_or_none()

            if orm_character:
                log.debug(f"Персонаж с character_id={character_id} найден.")
                return CharacterReadDTO.from_orm(orm_character)
            log.debug(f"Персонаж с character_id={character_id} не найден.")
            return None
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при получении персонажа {character_id}: {e}")
            raise

    async def get_characters(self, user_id: int, **kwargs) -> List[CharacterReadDTO]:
        """Возвращает список DTO персонажей для указанного пользователя."""
        log.debug(f"Запрос на получение списка персонажей для user_id={user_id}")
        stmt = select(Character).where(Character.user_id == user_id)
        try:
            result = await self.session.scalars(stmt)
            orm_characters_list = result.all()

            log.debug(f"Найдено {len(orm_characters_list)} персонажей для user_id={user_id}.")
            return [CharacterReadDTO.from_orm(orm_char) for orm_char in orm_characters_list]
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при получении списка персонажей для user_id={user_id}: {e}")
            raise

    async def delete_characters(self, character_id: int) -> None:
        """Удаляет персонажа по его ID."""
        log.debug(f"Запрос на удаление персонажа с character_id={character_id}")
        stmt = delete(Character).where(Character.character_id == character_id)
        try:
            await self.session.execute(stmt)
            log.info(f"Персонаж {character_id} был успешно удален.")
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при удалении персонажа {character_id}: {e}")
            raise

    async def update_character_game_stage(self, character_id: int, game_stage: str) -> None:
        """Обновляет игровую стадию персонажа."""
        log.debug(f"Запрос на обновление game_stage для character_id={character_id} на '{game_stage}'")
        stmt = update(Character).where(Character.character_id == character_id).values(game_stage=game_stage)
        try:
            await self.session.execute(stmt)
            log.debug(f"Стадия персонажа {character_id} была обновлена на: {game_stage}")
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при обновлении game_stage для character_id={character_id}: {e}")
            raise


class CharacterStatsRepoORM(ICharacterStatsRepo):
    """ORM-реализация репозитория для управления характеристиками персонажа."""

    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug(f"Инициализирован {self.__class__.__name__} с сессией: {session}")

    async def get_stats(self, character_id: int, **kwargs) -> Optional[CharacterStatsReadDTO]:
        """Возвращает DTO характеристик персонажа."""
        log.debug(f"Запрос на получение статов для character_id={character_id}")
        stmt = select(CharacterStats).where(CharacterStats.character_id == character_id)
        try:
            result = await self.session.execute(stmt)
            orm_stats = result.scalar_one_or_none()

            if orm_stats:
                log.debug(f"Статы для character_id={character_id} найдены.")
                return CharacterStatsReadDTO.from_orm(orm_stats)
            log.debug(f"Статы для character_id={character_id} не найдены.")
            return None
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при получении статов для character_id={character_id}: {e}")
            raise

    async def update_stats(self, character_id: int, stats_data: CharacterStatsUpdateDTO) -> None:
        """Полностью перезаписывает характеристики персонажа."""
        log.debug(f"Запрос на полное обновление статов для character_id={character_id}")
        stmt = (
            update(CharacterStats)
            .where(CharacterStats.character_id == character_id)
            .values(**stats_data.model_dump())
        )
        try:
            await self.session.execute(stmt)
            log.debug(f"Статы персонажа {character_id} были успешно обновлены.")
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при обновлении статов для character_id={character_id}: {e}")
            raise

    async def add_stats(self, character_id: int, stats_to_add: Dict[str, int]) -> Optional[CharacterStatsReadDTO]:
        """Атомарно добавляет значения к существующим статам и возвращает обновленные данные."""
        if not stats_to_add:
            log.warning(f"Вызван add_stats для character_id={character_id} с пустым словарем бонусов.")
            return None

        log.debug(f"Запрос на атомарное добавление статов для character_id={character_id}: {stats_to_add}")
        ALLOWED_STATS = {"strength", "agility", "endurance", "charisma", "intelligence", "perception", "luck"}
        values_to_update = {}
        for stat, value in stats_to_add.items():
            if stat in ALLOWED_STATS:
                orm_column = getattr(CharacterStats, stat)
                values_to_update[stat] = orm_column + value

        if not values_to_update:
            log.warning(f"В add_stats для character_id={character_id} не передано валидных статов.")
            return None

        stmt = (
            update(CharacterStats)
            .where(CharacterStats.character_id == character_id)
            .values(**values_to_update)
            .returning(CharacterStats)
        )
        try:
            result = await self.session.execute(stmt)
            orm_stats = result.scalar_one_or_none()
            if orm_stats:
                log.debug(f"Атомарное добавление статов для {character_id} выполнено успешно.")
                return CharacterStatsReadDTO.from_orm(orm_stats)
            log.warning(f"Не удалось вернуть обновленные статы после add_stats для character_id={character_id}.")
            return None
        except SQLAlchemyError as e:
            log.exception(f"Ошибка SQLAlchemy при атомарном добавлении статов для character_id={character_id}: {e}")
            raise
