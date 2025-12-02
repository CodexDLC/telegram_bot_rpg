from loguru import logger as log
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.schemas_dto.character_dto import (
    CharacterOnboardingUpdateDTO,
    CharacterReadDTO,
    CharacterShellCreateDTO,
    CharacterStatsReadDTO,
    CharacterStatsUpdateDTO,
)
from database.db_contract.i_characters_repo import ICharactersRepo, ICharacterStatsRepo
from database.model_orm.character import Character, CharacterStats
from database.model_orm.inventory import ResourceWallet
from database.model_orm.symbiote import CharacterSymbiote


class CharactersRepoORM(ICharactersRepo):
    """
    ORM-реализация репозитория для управления основными данными персонажей.

    Предоставляет методы для создания, обновления, получения и удаления
    персонажей, а также для управления их базовыми связями (статы, симбиот, кошелек).
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует CharactersRepoORM.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session
        log.debug(f"CharactersRepoORM | status=initialized session={session}")

    async def create_character_shell(self, character_data: CharacterShellCreateDTO) -> int:
        """
        Создает "оболочку" персонажа, включая связанные с ней статы, Симбиота и Кошелек.

        Args:
            character_data: DTO с `user_id` для создания оболочки.

        Returns:
            Уникальный идентификатор (`character_id`) созданной записи персонажа.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        log.debug(f"CharactersRepoORM | action=create_character_shell user_id={character_data.user_id}")
        try:
            orm_character = Character(**character_data.model_dump())
            orm_character.stats = CharacterStats()
            orm_character.symbiote = CharacterSymbiote()
            orm_character.wallet = ResourceWallet()

            self.session.add(orm_character)
            await self.session.flush()
            log.info(
                f"CharactersRepoORM | action=create_character_shell status=success char_id={orm_character.character_id}"
            )
            return orm_character.character_id
        except SQLAlchemyError:
            log.exception(
                f"CharactersRepoORM | action=create_character_shell status=failed user_id={character_data.user_id}"
            )
            raise

    async def update_character_onboarding(
        self, character_id: int, character_data: CharacterOnboardingUpdateDTO
    ) -> None:
        """
        Обновляет данные персонажа (имя, пол, стадия игры) после этапа онбординга.

        Args:
            character_id: Идентификатор персонажа для обновления.
            character_data: DTO с данными (name, gender, game_stage).

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        log.debug(
            f"CharactersRepoORM | action=update_character_onboarding char_id={character_id} data={character_data.model_dump_json()}"
        )
        stmt = update(Character).where(Character.character_id == character_id).values(**character_data.model_dump())
        try:
            await self.session.execute(stmt)
            log.info(f"CharactersRepoORM | action=update_character_onboarding status=success char_id={character_id}")
        except SQLAlchemyError:
            log.exception(
                f"CharactersRepoORM | action=update_character_onboarding status=failed char_id={character_id}"
            )
            raise

    async def get_character(self, character_id: int) -> CharacterReadDTO | None:
        """
        Находит и возвращает одного персонажа по его `character_id`.

        Args:
            character_id: Уникальный идентификатор персонажа.

        Returns:
            DTO `CharacterReadDTO` с данными персонажа, если он найден,
            иначе - None.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        log.debug(f"CharactersRepoORM | action=get_character char_id={character_id}")
        stmt = select(Character).where(Character.character_id == character_id)
        try:
            result = await self.session.execute(stmt)
            orm_character = result.scalar_one_or_none()

            if orm_character:
                log.debug(f"CharactersRepoORM | action=get_character status=found char_id={character_id}")
                return CharacterReadDTO.model_validate(orm_character)
            log.debug(f"CharactersRepoORM | action=get_character status=not_found char_id={character_id}")
            return None
        except SQLAlchemyError:
            log.exception(f"CharactersRepoORM | action=get_character status=failed char_id={character_id}")
            raise

    async def get_characters(self, user_id: int) -> list[CharacterReadDTO]:
        """
        Возвращает список DTO персонажей для указанного пользователя.

        Args:
            user_id: Идентификатор пользователя.

        Returns:
            Список DTO `CharacterReadDTO` персонажей.
            Если персонажей нет, возвращает пустой список.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        log.debug(f"CharactersRepoORM | action=get_characters user_id={user_id}")
        stmt = select(Character).where(Character.user_id == user_id)
        try:
            result = await self.session.scalars(stmt)
            orm_characters_list = result.all()

            log.debug(
                f"CharactersRepoORM | action=get_characters status=found count={len(orm_characters_list)} user_id={user_id}"
            )
            return [CharacterReadDTO.model_validate(orm_char) for orm_char in orm_characters_list]
        except SQLAlchemyError:
            log.exception(f"CharactersRepoORM | action=get_characters status=failed user_id={user_id}")
            raise

    async def delete_characters(self, character_id: int) -> None:
        """
        Удаляет персонажа и все связанные с ним данные из базы данных.

        Args:
            character_id: Идентификатор персонажа для удаления.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        log.debug(f"CharactersRepoORM | action=delete_characters char_id={character_id}")
        stmt = delete(Character).where(Character.character_id == character_id)
        try:
            await self.session.execute(stmt)
            log.info(f"CharactersRepoORM | action=delete_characters status=success char_id={character_id}")
        except SQLAlchemyError:
            log.exception(f"CharactersRepoORM | action=delete_characters status=failed char_id={character_id}")
            raise

    async def update_character_game_stage(self, character_id: int, game_stage: str) -> None:
        """
        Обновляет игровую стадию (`game_stage`) персонажа.

        Args:
            character_id: Идентификатор персонажа для обновления.
            game_stage: Новое значение игровой стадии.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        log.debug(
            f"CharactersRepoORM | action=update_character_game_stage char_id={character_id} new_stage='{game_stage}'"
        )
        stmt = update(Character).where(Character.character_id == character_id).values(game_stage=game_stage)
        try:
            await self.session.execute(stmt)
            log.info(
                f"CharactersRepoORM | action=update_character_game_stage status=success char_id={character_id} new_stage='{game_stage}'"
            )
        except SQLAlchemyError:
            log.exception(
                f"CharactersRepoORM | action=update_character_game_stage status=failed char_id={character_id}"
            )
            raise


class CharacterStatsRepoORM(ICharacterStatsRepo):
    """
    ORM-реализация репозитория для управления характеристиками персонажа.

    Предоставляет методы для получения, обновления и атомарного добавления
    значений к характеристикам персонажа.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует CharacterStatsRepoORM.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session
        log.debug(f"CharacterStatsRepoORM | status=initialized session={session}")

    async def get_stats(self, character_id: int) -> CharacterStatsReadDTO | None:
        """
        Возвращает DTO характеристик персонажа.

        Args:
            character_id: Идентификатор персонажа, чьи характеристики нужны.

        Returns:
            DTO `CharacterStatsReadDTO` с характеристиками, если они найдены,
            иначе - None.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        log.debug(f"CharacterStatsRepoORM | action=get_stats char_id={character_id}")
        stmt = select(CharacterStats).where(CharacterStats.character_id == character_id)
        try:
            result = await self.session.execute(stmt)
            orm_stats = result.scalar_one_or_none()

            if orm_stats:
                log.debug(f"CharacterStatsRepoORM | action=get_stats status=found char_id={character_id}")
                return CharacterStatsReadDTO.model_validate(orm_stats)
            log.debug(f"CharacterStatsRepoORM | action=get_stats status=not_found char_id={character_id}")
            return None
        except SQLAlchemyError:
            log.exception(f"CharacterStatsRepoORM | action=get_stats status=failed char_id={character_id}")
            raise

    async def update_stats(self, character_id: int, stats_data: CharacterStatsUpdateDTO) -> None:
        """
        Полностью перезаписывает все характеристики персонажа.

        Args:
            character_id: Идентификатор персонажа для обновления.
            stats_data: DTO с полным набором новых характеристик.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        log.debug(
            f"CharacterStatsRepoORM | action=update_stats char_id={character_id} data={stats_data.model_dump_json()}"
        )
        stmt = (
            update(CharacterStats).where(CharacterStats.character_id == character_id).values(**stats_data.model_dump())
        )
        try:
            await self.session.execute(stmt)
            log.info(f"CharacterStatsRepoORM | action=update_stats status=success char_id={character_id}")
        except SQLAlchemyError:
            log.exception(f"CharacterStatsRepoORM | action=update_stats status=failed char_id={character_id}")
            raise

    async def add_stats(self, character_id: int, stats_to_add: dict[str, int]) -> CharacterStatsReadDTO | None:
        """
        Атомарно добавляет значения к существующим характеристикам персонажа.

        Инкрементально обновляет только переданные характеристики и возвращает
        их новое полное состояние.

        Args:
            character_id: Идентификатор персонажа.
            stats_to_add: Словарь, где ключ - название характеристики,
                          а значение - число для добавления (может быть отрицательным).

        Returns:
            DTO `CharacterStatsReadDTO` с обновленными характеристиками
            персонажа или None, если персонаж не найден.

        Raises:
            SQLAlchemyError: В случае ошибки взаимодействия с базой данных.
        """
        if not stats_to_add:
            log.warning(f"CharacterStatsRepoORM | action=add_stats reason='Empty stats_to_add' char_id={character_id}")
            return None

        log.debug(f"CharacterStatsRepoORM | action=add_stats char_id={character_id} stats={stats_to_add}")
        allowed_stats = {
            "strength",
            "agility",
            "endurance",
            "intelligence",
            "wisdom",
            "men",
            "perception",
            "charisma",
            "luck",
        }
        values_to_update = {}
        for stat, value in stats_to_add.items():
            if stat in allowed_stats:
                orm_column = getattr(CharacterStats, stat)
                values_to_update[stat] = orm_column + value

        if not values_to_update:
            log.warning(
                f"CharacterStatsRepoORM | action=add_stats reason='No valid stats to update' char_id={character_id}"
            )
            return None

        stmt = update(CharacterStats).where(CharacterStats.character_id == character_id).values(**values_to_update)

        try:
            await self.session.execute(stmt)
            await self.session.flush()

            updated_stats_dto = await self.get_stats(character_id=character_id)

            if updated_stats_dto:
                log.info(f"CharacterStatsRepoORM | action=add_stats status=success char_id={character_id}")
                return updated_stats_dto

            log.error(
                f"CharacterStatsRepoORM | action=add_stats status=failed reason='Could not retrieve updated stats' char_id={character_id}"
            )
            return None

        except SQLAlchemyError:
            log.exception(f"CharacterStatsRepoORM | action=add_stats status=failed char_id={character_id}")
            raise
