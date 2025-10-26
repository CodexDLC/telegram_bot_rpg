# database/repositories/__init__.py
import aiosqlite

from database.db_contract.i_users_repo import IUserRepo
from database.repositories.SQLite.users_repo import UsersRepo


def get_user_repo(db: aiosqlite.Connection) -> IUserRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ место, которое знает,
    какую реализацию IUserRepo мы используем.
    """
    # Сейчас мы жестко возвращаем SQLite-реализацию
    return UsersRepo(db)


