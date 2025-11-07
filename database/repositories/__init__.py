# database/repositories/__init__.py

# 1. Мы импортируем AsyncSession из SQLAlchemy
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_contract.i_skill_repo import ISkillRateRepo, ISkillProgressRepo
# 2. Мы импортируем КОНТРАКТЫ (Интерфейсы)
from database.db_contract.i_users_repo import IUserRepo
from database.db_contract.i_characters_repo import ICharactersRepo, ICharacterStatsRepo
from database.repositories.ORM.characters_repo_orm import CharactersRepoORM, CharacterStatsRepoORM
from database.repositories.ORM.skill_repo import SkillRateRepo, SkillProgressRepo
from database.repositories.ORM.users_repo_orm import UsersRepoORM



def get_user_repo(session: AsyncSession) -> IUserRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ место, которое знает,
    какую реализацию IUserRepo мы используем.
    """
    # Сейчас мы возвращаем ORM-реализацию
    return UsersRepoORM(session)


def get_character_repo(session: AsyncSession) -> ICharactersRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ место, которое знает,
    какую реализацию ICharacterRepo мы используем.
    """
    return CharactersRepoORM(session)


def get_character_stats_repo(session: AsyncSession) -> ICharacterStatsRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ
    место, которое знает,
    какую реализацию ICharacterStats мы используем.
    """
    return CharacterStatsRepoORM(session)

def get_skill_rate_repo(session: AsyncSession) -> ISkillRateRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ
    место, которое знает,
    какую реализацию ISkillRateRepo мы используем.
    """
    return SkillRateRepo(session)

def get_skill_progress_repo(session: AsyncSession) -> ISkillProgressRepo:

    """
    Эта функция - ЕДИНСТВЕННОЕ
    место, которое знает,
    какую реализацию ISkillProgressRepo мы используем.
    """
    return SkillProgressRepo(session)

