import logging
from dataclasses import asdict
from typing import Dict

import aiosqlite

from app.resources.models.character_dto import CharacterReadDTO, CharacterCreateDTO, CharacterStatsReadDTO, \
    CharacterStatsUpdateDTO
from database.db_contract.i_characters_repo import ICharactersRepo, ICharacterStatsRepo

log = logging.getLogger(__name__)


class CharacterRepo(ICharactersRepo):
    def __init__(self, db: aiosqlite.Connection):
        self.db = db


    async def create_character(self, character_data: CharacterCreateDTO) -> int:
        """
        Создает персонажа.
        """
        sql = """
                    -- Простой INSERT, без ON CONFLICT
                    INSERT INTO characters (user_id, name, gender, game_stage)
                    VALUES (:user_id, :name, :gender, :game_stage)
                """

        character_data_dict = asdict(character_data)
        cursor = await self.db.execute(sql, character_data_dict)
        return cursor.lastrowid

    async def get_character(self, character_id: int, **kwargs) -> CharacterReadDTO | None:
        """
        Возвращает персонажа.
        """
        sql = """
                SELECT * FROM characters WHERE character_id = ?                        
        """

        async with self.db.execute(sql, (character_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return CharacterReadDTO(**row)
            return None

    async def get_characters(self, user_id: int, **kwargs) -> list:
        """
        Возвращает список персонажей.
        """
        sql = """
                SELECT * FROM characters WHERE user_id = ?                        
        """

        async with self.db.execute(sql, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [CharacterReadDTO(**row) for row in rows]


    async def delete_characters(self,character_id: int):
        """
        Удаляет персонажа.
        """

        sql = """
                DELETE FROM characters WHERE character_id = ?                        
        """

        await self.db.execute(sql, (character_id,))

    async def update_character_game_stage(self, character_id: int, game_stage: str):
        """
        Обновляет стадию персонажа.
        """
        sql = """
                UPDATE characters
                SET game_stage = :game_stage
                WHERE character_id = :character
                """
        data = {
            'game_stage': game_stage,
            'character': character_id
        }
        await self.db.execute(sql, data)
        log.debug(f"Стадия персонажа {character_id} была обновлена на: {game_stage}")


class CharacterStatsRepo(ICharacterStatsRepo):
    def __init__(self, db: aiosqlite.Connection):
        self.db = db


    async def get_stats(self, character_id: int, **kwargs) -> CharacterStatsReadDTO | None:
        """
        Возвращает персонажа.
        """
        sql = """
                SELECT * FROM character_stats WHERE character_id = ?                        
        """

        async with self.db.execute(sql, (character_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                log.debug(f"Данные получены {row}")
                return CharacterStatsReadDTO(**row)
            return None

    async def update_stats(self,character_id: int, stats_data: CharacterStatsUpdateDTO):
        """
        Обновляет персонажа.
        """
        sql = """
                UPDATE character_stats
                SET strength = :strength
                , agility = :agility
                , endurance = :endurance
                , charisma = :charisma
                , intelligence = :intelligence
                , perception = :perception
                , luck = :luck
                WHERE character_id = :character_id
        """

        stats_data_dict = asdict(stats_data)
        stats_data_dict['character_id'] = character_id

        await self.db.execute(sql, stats_data_dict)
        log.debug(f"Stats персонажа были обновлены; {stats_data_dict}")




    async def add_stats(self, character_id: int, stats_to_add: Dict[str, int]):
        """
        Атомарно добавляет значения к существующим статам, используя
        динамический SQL-запрос.
        """

        # 1. Проверяем, есть ли что добавлять
        if not stats_to_add:
            log.warning("Вызван add_stats с пустым словарем бонусов.")
            return None

        # 2. Белый список статов (для безопасности)
        ALLOWED_STATS = {
            "strength", "agility", "endurance",
            "charisma", "intelligence", "perception", "luck"
        }

        # 3. Готовим части SQL-запроса
        set_clauses = []  # Список "strength = strength + ?"
        params = []  # Список значений [2, 1, ...]

        for stat, value in stats_to_add.items():
            if stat in ALLOWED_STATS:
                set_clauses.append(f"{stat} = {stat} + ?")
                params.append(value)
            else:
                log.warning(f"Проигнорирован неизвестный стат в add_stats: {stat}")

        # 4. Если (по какой-то причине) не осталось валидных статов
        if not set_clauses:
            return None

        # 5. Собираем запрос
        # ("strength = strength + ?, agility = agility + ?")
        query_set_part = ", ".join(set_clauses)

        # Добавляем ID персонажа в конец списка параметров
        params.append(character_id)

        sql = f"""
            UPDATE character_stats
            SET {query_set_part}
            WHERE character_id = ?
            RETURNING *
        """

        # 6. Выполняем
        log.debug(f"Выполняем атомарное добавление статов для {character_id}: {stats_to_add}")
        async with self.db.execute(sql, tuple(params)) as cursor:
            row = await cursor.fetchone()

            if row:
                # Мы вернули обновленные данные и сразу пакуем их в DTO
                return CharacterStatsReadDTO(**row)

            return None