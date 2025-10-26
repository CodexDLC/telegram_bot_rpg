from dataclasses import asdict

import aiosqlite

from app.resources.models.character_dto import CharacterReadDTO, CharacterCreateDTO
from database.db_contract.i_characters_repo import ICharactersRepo


class CharacterRepo(ICharactersRepo):
    def __init__(self, db: aiosqlite.Connection):
        self.db = db


    async def create_character(self, character_data: CharacterCreateDTO) -> None:
        """
        Создает персонажа.
        """
        sql = """
                    -- Простой INSERT, без ON CONFLICT
                    INSERT INTO characters (user_id, name, gender)
                    VALUES (:user_id, :name, :gender)
                """

        character_data_dict = asdict(character_data)
        await self.db.execute(sql, character_data_dict)


    async def get_character(self, character_id: int) -> CharacterReadDTO | None:
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

    async def get_characters(self, user_id: int) -> list:
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



