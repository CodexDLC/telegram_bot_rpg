import logging
from dataclasses import asdict
from typing import Optional, List

import aiosqlite


from app.resources.models.user_dto import UserUpsertDTO, UserDTO
from database.db_contract.i_users_repo import IUserRepo

log = logging.getLogger(__name__)

class UsersRepo(IUserRepo):
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def upsert_user(self, user: UserUpsertDTO) -> None:
        """
        Создает или обновляет пользователя, используя 'входную' DTO.
        """

        sql = """
                    INSERT INTO users (
                        telegram_id, first_name, username, 
                        last_name, language_code, is_premium
                    )
                    VALUES (
                        :telegram_id, :first_name, :username, 
                        :last_name, :language_code, :is_premium
                    )
                    ON CONFLICT (telegram_id) DO UPDATE SET
                        first_name = excluded.first_name,
                        username = excluded.username,
                        last_name = excluded.last_name,
                        language_code = excluded.language_code,
                        is_premium = excluded.is_premium,
                        updated_at = (STRFTIME('%Y-%m-%d %H:%M:%f', 'now'))
        """
        user_data_dict = asdict(user)

        await self.db.execute(sql, user_data_dict)


    async def get_user(self, telegram_id: int, **kwargs) -> Optional[UserDTO]:
        """
        Возвращает 'полную' DTO пользователя из БД.
        """
        sql = """
                SELECT * FROM users WHERE telegram_id = ?                        
        """

        async with self.db.execute(sql, (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return UserDTO(**row)
            return None

    async def get_users(self) -> List[UserDTO]:
        """
        Возвращает список 'полных' DTO (для админки).
        """
        sql = """
                SELECT * FROM users
        """
        async with self.db.execute(sql) as cursor:
            rows = await cursor.fetchall()  # Получаем List[aiosqlite.Row]


            return [UserDTO(**row) for row in rows]
