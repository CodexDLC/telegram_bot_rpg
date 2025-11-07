# app/database/repositories/SQLite/users_repo.py
import logging
from typing import Optional, List

import aiosqlite

from app.resources.schemas_dto.user_dto import UserUpsertDTO, UserDTO
from database.db_contract.i_users_repo import IUserRepo

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


class UsersRepo(IUserRepo):
    """
    Репозиторий для управления пользователями в базе данных SQLite.

    Attributes:
        db (aiosqlite.Connection): Асинхронное подключение к базе данных.
    """

    def __init__(self, db: aiosqlite.Connection):
        """
        Инициализирует репозиторий пользователей.

        Args:
            db (aiosqlite.Connection): Экземпляр подключения к базе данных.
        """
        self.db = db
        log.debug(f"Инициализирован {self.__class__.__name__} с подключением: {db}")

    async def upsert_user(self, user: UserUpsertDTO) -> None:
        """
        Создает нового пользователя или обновляет существующего.

        Использует операцию 'INSERT ... ON CONFLICT ... DO UPDATE' (UPSERT)
        для атомарного создания или обновления записи пользователя на основе
        его `telegram_id`.

        Args:
            user (UserUpsertDTO): DTO с данными для создания/обновления.

        Returns:
            None
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
        user_data_dict = user.model_dump()
        log.debug(f"Выполнение SQL-запроса 'upsert_user' для telegram_id={user.telegram_id} с данными: {user_data_dict}")

        try:
            await self.db.execute(sql, user_data_dict)
            # Не вызываем commit(), так как предполагается, что управление
            # транзакциями происходит на более высоком уровне (в Unit of Work).
        except Exception as e:
            log.exception(f"Произошла ошибка при выполнении 'upsert_user' для telegram_id={user.telegram_id}: {e}")
            # Пробрасываем исключение дальше, чтобы UoW мог откатить транзакцию.
            raise

    async def get_user(self, telegram_id: int, **kwargs) -> Optional[UserDTO]:
        """
        Возвращает полную DTO пользователя по его telegram_id.

        Args:
            telegram_id (int): Уникальный идентификатор пользователя в Telegram.
            **kwargs: Дополнительные аргументы (не используются в этой реализации).

        Returns:
            Optional[UserDTO]: DTO пользователя, если он найден, иначе None.
        """
        sql = "SELECT * FROM users WHERE telegram_id = ?"
        log.debug(f"Выполнение SQL-запроса 'get_user' для telegram_id={telegram_id}")

        try:
            async with self.db.execute(sql, (telegram_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    log.debug(f"Пользователь с telegram_id={telegram_id} найден. Данные: {dict(row)}")
                    # Преобразуем aiosqlite.Row в словарь, а затем в Pydantic модель.
                    # model_validate ожидает dict, а не aiosqlite.Row.
                    return UserDTO.model_validate(dict(row))
                else:
                    log.debug(f"Пользователь с telegram_id={telegram_id} не найден.")
                    return None
        except Exception as e:
            log.exception(f"Произошла ошибка при выполнении 'get_user' для telegram_id={telegram_id}: {e}")
            raise

    async def get_users(self) -> List[UserDTO]:
        """
        Возвращает список всех пользователей.

        Предназначено для использования в административных панелях или для отладки.

        Returns:
            List[UserDTO]: Список DTO всех пользователей в базе данных.
        """
        sql = "SELECT * FROM users"
        log.debug("Выполнение SQL-запроса 'get_users' для получения всех пользователей.")

        try:
            async with self.db.execute(sql) as cursor:
                rows = await cursor.fetchall()
                log.debug(f"Найдено {len(rows)} пользователей.")
                # Аналогично get_user, преобразуем каждую строку в dict перед валидацией.
                return [UserDTO.model_validate(dict(row)) for row in rows]
        except Exception as e:
            log.exception(f"Произошла ошибка при выполнении 'get_users': {e}")
            raise
