# database/repositories/__init__.py
import aiosqlite

from database.db_contract.i_users_repo import IUserRepo
from database.repositories.SQLite.characters_repo import CharacterRepo, CharacterStatsRepo
from database.repositories.SQLite.users_repo import UsersRepo


def get_user_repo(db: aiosqlite.Connection) -> IUserRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ место, которое знает,
    какую реализацию IUserRepo мы используем.
    """
    # Сейчас мы жестко возвращаем SQLite-реализацию
    return UsersRepo(db)


def get_character_repo(db: aiosqlite.Connection) -> CharacterRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ место, которое знает,
    какую реализацию ICharacterRepo мы используем.
    """
    # Сейчас мы жестко возвращаем SQLite-реализацию
    return CharacterRepo(db)

def get_character_stats_repo(db: aiosqlite.Connection) -> CharacterStats:
    """
    Эта функция - ЕДИНСТВЕННОЕ
    место, которое знает,
    какую реализацию ICharacterStats мы используем.
    """
    # Сейчас мы жестко возвращаем SQLite-реализацию
    return CharacterStatsRepo(db)