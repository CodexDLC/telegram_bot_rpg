# app/database/repositories/SQLite/characters_repo.py
import logging
from typing import Dict, Optional, List

import aiosqlite

# TODO: Убедиться, что CharacterCreateDTO импортирован правильно.
#  В предоставленном коде он отсутствует.
# from app.resources.schemas_dto.character_dto import CharacterCreateDTO
from app.resources.schemas_dto.character_dto import (
    CharacterReadDTO, CharacterStatsReadDTO,
    CharacterStatsUpdateDTO, CharacterCreateDTO)  # Предполагаемый импорт

from database.db_contract.i_characters_repo import ICharactersRepo, ICharacterStatsRepo

log = logging.getLogger(__name__)

# =================================================================================
#
#       !!! LEGACY CODE !!!
#
#   Этот репозиторий использует SQLite. В новой версии проекта
#   планируется переход на PostgreSQL с использованием SQLAlchemy.
#   Вносить изменения в этот файл не рекомендуется.
#
# =================================================================================


class CharacterRepo(ICharactersRepo):
    """
    Репозиторий для управления персонажами в базе данных SQLite.

    Attributes:
        db (aiosqlite.Connection): Асинхронное подключение к базе данных.
    """

    def __init__(self, db: aiosqlite.Connection):
        """
        Инициализирует репозиторий персонажей.

        Args:
            db (aiosqlite.Connection): Экземпляр подключения к базе данных.
        """
        self.db = db
        log.debug(f"Инициализирован {self.__class__.__name__} с подключением: {db}")

    async def create_character(self, character_data: CharacterCreateDTO) -> int:
        """
        Создает нового персонажа в базе данных.

        Args:
            character_data (CharacterCreateDTO): DTO с данными для создания персонажа.

        Returns:
            int: ID созданного персонажа (`lastrowid`).
        """
        sql = """
            INSERT INTO characters (user_id, name, gender, game_stage)
            VALUES (:user_id, :name, :gender, :game_stage)
        """
        character_data_dict = character_data.model_dump()
        log.debug(f"Выполнение SQL-запроса 'create_character' с данными: {character_data_dict}")

        try:
            cursor = await self.db.execute(sql, character_data_dict)
            new_character_id = cursor.lastrowid
            log.debug(f"Персонаж успешно создан с ID: {new_character_id}")
            return new_character_id
        except Exception as e:
            log.exception(f"Произошла ошибка при выполнении 'create_character': {e}")
            raise

    async def get_character(self, character_id: int, **kwargs) -> Optional[CharacterReadDTO]:
        """
        Возвращает данные персонажа по его ID.

        Args:
            character_id (int): Уникальный идентификатор персонажа.
            **kwargs: Дополнительные аргументы (не используются).

        Returns:
            Optional[CharacterReadDTO]: DTO персонажа, если найден, иначе None.
        """
        sql = "SELECT * FROM characters WHERE character_id = ?"
        log.debug(f"Выполнение SQL-запроса 'get_character' для character_id={character_id}")

        try:
            async with self.db.execute(sql, (character_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    log.debug(f"Персонаж с character_id={character_id} найден.")
                    return CharacterReadDTO.model_validate(dict(row))
                else:
                    log.debug(f"Персонаж с character_id={character_id} не найден.")
                    return None
        except Exception as e:
            log.exception(f"Произошла ошибка при выполнении 'get_character' для character_id={character_id}: {e}")
            raise

    async def get_characters(self, user_id: int, **kwargs) -> List[CharacterReadDTO]:
        """
        Возвращает список всех персонажей, принадлежащих пользователю.

        Args:
            user_id (int): ID пользователя, чьих персонажей нужно найти.
            **kwargs: Дополнительные аргументы (не используются).

        Returns:
            List[CharacterReadDTO]: Список DTO персонажей.
        """
        sql = "SELECT * FROM characters WHERE user_id = ?"
        log.debug(f"Выполнение SQL-запроса 'get_characters' для user_id={user_id}")

        try:
            async with self.db.execute(sql, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                log.debug(f"Найдено {len(rows)} персонажей для user_id={user_id}.")
                return [CharacterReadDTO.model_validate(dict(row)) for row in rows]
        except Exception as e:
            log.exception(f"Произошла ошибка при выполнении 'get_characters' для user_id={user_id}: {e}")
            raise

    async def delete_characters(self, character_id: int) -> None:
        """
        Удаляет персонажа по его ID.

        Args:
            character_id (int): ID персонажа для удаления.

        Returns:
            None
        """
        sql = "DELETE FROM characters WHERE character_id = ?"
        log.debug(f"Выполнение SQL-запроса 'delete_characters' для character_id={character_id}")

        try:
            await self.db.execute(sql, (character_id,))
            log.debug(f"Персонаж с character_id={character_id} успешно удален.")
        except Exception as e:
            log.exception(f"Произошла ошибка при выполнении 'delete_characters' для character_id={character_id}: {e}")
            raise

    async def update_character_game_stage(self, character_id: int, game_stage: str) -> None:
        """
        Обновляет игровою стадию (этап) персонажа.

        Args:
            character_id (int): ID персонажа для обновления.
            game_stage (str): Новая игровая стадия.

        Returns:
            None
        """
        sql = "UPDATE characters SET game_stage = :game_stage WHERE character_id = :character_id"
        params = {'game_stage': game_stage, 'character_id': character_id}
        log.debug(f"Выполнение SQL-запроса 'update_character_game_stage' с параметрами: {params}")

        try:
            await self.db.execute(sql, params)
            log.debug(f"Стадия персонажа {character_id} обновлена на: {game_stage}")
        except Exception as e:
            log.exception(f"Произошла ошибка при обновлении стадии для character_id={character_id}: {e}")
            raise


class CharacterStatsRepo(ICharacterStatsRepo):
    """
    Репозиторий для управления характеристиками (статами) персонажа в SQLite.

    Attributes:
        db (aiosqlite.Connection): Асинхронное подключение к базе данных.
    """

    def __init__(self, db: aiosqlite.Connection):
        """
        Инициализирует репозиторий характеристик.

        Args:
            db (aiosqlite.Connection): Экземпляр подключения к базе данных.
        """
        self.db = db
        log.debug(f"Инициализирован {self.__class__.__name__} с подключением: {db}")

    async def get_stats(self, character_id: int, **kwargs) -> Optional[CharacterStatsReadDTO]:
        """
        Возвращает характеристики персонажа по его ID.

        Args:
            character_id (int): ID персонажа.
            **kwargs: Дополнительные аргументы (не используются).

        Returns:
            Optional[CharacterStatsReadDTO]: DTO характеристик, если найдены, иначе None.
        """
        sql = "SELECT * FROM character_stats WHERE character_id = ?"
        log.debug(f"Выполнение SQL-запроса 'get_stats' для character_id={character_id}")

        try:
            async with self.db.execute(sql, (character_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    log.debug(f"Характеристики для character_id={character_id} найдены.")
                    return CharacterStatsReadDTO.model_validate(dict(row))
                else:
                    log.debug(f"Характеристики для character_id={character_id} не найдены.")
                    return None
        except Exception as e:
            log.exception(f"Произошла ошибка при выполнении 'get_stats' для character_id={character_id}: {e}")
            raise

    async def update_stats(self, character_id: int, stats_data: CharacterStatsUpdateDTO) -> None:
        """
        Полностью перезаписывает характеристики персонажа.

        Args:
            character_id (int): ID персонажа для обновления.
            stats_data (CharacterStatsUpdateDTO): DTO с новыми значениями характеристик.

        Returns:
            None
        """
        sql = """
            UPDATE character_stats
            SET strength = :strength, agility = :agility, endurance = :endurance,
                charisma = :charisma, intelligence = :intelligence,
                perception = :perception, luck = :luck
            WHERE character_id = :character_id
        """
        stats_data_dict = stats_data.model_dump()
        stats_data_dict['character_id'] = character_id
        log.debug(f"Выполнение SQL-запроса 'update_stats' для character_id={character_id} с данными: {stats_data_dict}")

        try:
            await self.db.execute(sql, stats_data_dict)
            log.debug(f"Характеристики персонажа {character_id} успешно обновлены.")
        except Exception as e:
            log.exception(f"Произошла ошибка при выполнении 'update_stats' для character_id={character_id}: {e}")
            raise

    async def add_stats(self, character_id: int, stats_to_add: Dict[str, int]) -> Optional[CharacterStatsReadDTO]:
        """
        Атомарно добавляет значения к существующим характеристикам.

        Динамически формирует SQL-запрос для инкрементального обновления
        только тех полей, которые переданы в `stats_to_add`.

        Args:
            character_id (int): ID персонажа.
            stats_to_add (Dict[str, int]): Словарь, где ключ - название характеристики,
                                          а значение - число для добавления.

        Returns:
            Optional[CharacterStatsReadDTO]: Обновленные характеристики персонажа,
                                             если операция прошла успешно, иначе None.
        """
        if not stats_to_add:
            log.warning(f"Вызван 'add_stats' для character_id={character_id} с пустым словарем бонусов.")
            return None

        ALLOWED_STATS = {
            "strength", "agility", "endurance", "charisma",
            "intelligence", "perception", "luck"
        }

        set_clauses = []
        params = []

        for stat, value in stats_to_add.items():
            if stat in ALLOWED_STATS:
                set_clauses.append(f"{stat} = {stat} + ?")
                params.append(value)
            else:
                log.warning(f"Проигнорирован неизвестный стат в 'add_stats' для character_id={character_id}: {stat}")

        if not set_clauses:
            log.warning(f"В 'add_stats' для character_id={character_id} не передано ни одного валидного стата.")
            return None

        query_set_part = ", ".join(set_clauses)
        params.append(character_id)

        sql = f"""
            UPDATE character_stats
            SET {query_set_part}
            WHERE character_id = ?
            RETURNING *
        """
        log.debug(f"Выполнение SQL-запроса 'add_stats' для character_id={character_id} с параметрами: {tuple(params)}")

        try:
            async with self.db.execute(sql, tuple(params)) as cursor:
                row = await cursor.fetchone()
                if row:
                    log.debug(f"Атомарное добавление статов для character_id={character_id} успешно выполнено.")
                    return CharacterStatsReadDTO.model_validate(dict(row))
                return None
        except Exception as e:
            log.exception(f"Произошла ошибка при выполнении 'add_stats' для character_id={character_id}: {e}")
            raise
