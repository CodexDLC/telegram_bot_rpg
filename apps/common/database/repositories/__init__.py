# database/repositories/__init__.py

# 1. Мы импортируем AsyncSession из SQLAlchemy
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.db_contract.i_characters_repo import ICharactersRepo, ICharacterStatsRepo
from apps.common.database.db_contract.i_inventory_repo import IInventoryRepo
from apps.common.database.db_contract.i_leaderboard_repo import ILeaderboardRepo
from apps.common.database.db_contract.i_monster_repository import IMonsterRepository
from apps.common.database.db_contract.i_skill_repo import ISkillProgressRepo, ISkillRateRepo
from apps.common.database.db_contract.i_symbiote_repo import ISymbioteRepo
from apps.common.database.db_contract.i_users_repo import IUserRepo
from apps.common.database.db_contract.i_wallet_repo import IWalletRepo
from apps.common.database.db_contract.i_world_repo import IWorldRepo
from apps.common.database.repositories.ORM.characters_repo_orm import CharactersRepoORM, CharacterStatsRepoORM
from apps.common.database.repositories.ORM.inventory_repo import InventoryRepo
from apps.common.database.repositories.ORM.leaderboard_repo import LeaderboardRepoORM
from apps.common.database.repositories.ORM.monster_repository import MonsterRepository
from apps.common.database.repositories.ORM.skill_repo import SkillProgressRepo, SkillRateRepo
from apps.common.database.repositories.ORM.symbiote_repo import SymbioteRepoORM
from apps.common.database.repositories.ORM.users_repo_orm import UsersRepoORM
from apps.common.database.repositories.ORM.wallet_repo import WalletRepoORM
from apps.common.database.repositories.ORM.world_repo import WorldRepoORM


def get_user_repo(session: AsyncSession) -> IUserRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ место, которое знает,
    какую реализацию IUserRepo мы используем.
    """
    # Сейчас мы возвращаем ORM-реализацию
    return UsersRepoORM(session=session)


def get_character_repo(session: AsyncSession) -> ICharactersRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ место, которое знает,
    какую реализацию ICharacterRepo мы используем.
    """
    return CharactersRepoORM(session=session)


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
    return SkillRateRepo(session=session)


def get_skill_progress_repo(session: AsyncSession) -> ISkillProgressRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ
    место, которое знает,
    какую реализацию ISkillProgressRepo мы используем.
    """
    return SkillProgressRepo(session)


def get_inventory_repo(session: AsyncSession) -> IInventoryRepo:
    """
    Эта функция - ЕДИНСТВЕННОЕ
    место, которое знает,
    какую реализацию IInventoryRepo
    мы используем.
    """

    return InventoryRepo(session=session)


def get_symbiote_repo(session: AsyncSession) -> ISymbioteRepo:
    """
    Возвращает репозиторий для работы с Симбиотом.
    """
    return SymbioteRepoORM(session=session)


def get_wallet_repo(session: AsyncSession) -> IWalletRepo:
    """
    Возвращает репозиторий для работы с Кошельком.
    """
    return WalletRepoORM(session=session)


def get_leaderboard_repo(session: AsyncSession) -> ILeaderboardRepo:
    """
    Возвращает репозиторий для работы с Лидербордом.
    """

    return LeaderboardRepoORM(session=session)


def get_world_repo(session: AsyncSession) -> IWorldRepo:
    """
    Возвращает репозиторий для работы с Миром.
    """
    return WorldRepoORM(session=session)


def get_monster_repo(session: AsyncSession) -> IMonsterRepository:
    """
    Единственное место, которое знает, какую реализацию IMonsterRepository мы используем.
    """
    return MonsterRepository(session=session)
