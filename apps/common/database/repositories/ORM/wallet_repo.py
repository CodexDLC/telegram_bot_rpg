from typing import Literal

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.db_contract.i_wallet_repo import IWalletRepo
from apps.common.database.model_orm.inventory import ResourceWallet

# Три столпа
ResourceTypeGroup = Literal["currency", "resources", "components"]


class WalletRepoORM(IWalletRepo):
    """
    ORM-реализация репозитория для управления Кошельком Ресурсов.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_wallet_exists(self, char_id: int) -> None:
        """Создает пустой кошелек, если его нет."""
        stmt = sqlite_insert(ResourceWallet).values(character_id=char_id).on_conflict_do_nothing()
        try:
            await self.session.execute(stmt)
        except SQLAlchemyError:
            log.exception(f"WalletRepo | Failed to ensure wallet for {char_id}")
            raise

    async def get_wallet(self, char_id: int) -> ResourceWallet:
        """Возвращает объект кошелька."""
        await self.ensure_wallet_exists(char_id)
        stmt = select(ResourceWallet).where(ResourceWallet.character_id == char_id)
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one()
        except SQLAlchemyError:
            log.exception(f"WalletRepo | Failed to get wallet for {char_id}")
            raise

    async def get_resource_amount(self, char_id: int, group: ResourceTypeGroup, key: str) -> int:
        """
        Возвращает количество ресурса.

        Args:
            group: 'currency', 'resources' или 'components'.
        """
        try:
            wallet = await self.get_wallet(char_id)
            # Безопасно берем нужный JSON-словарь
            group_data = getattr(wallet, group, {}) or {}
            return group_data.get(key, 0)
        except AttributeError:
            log.error(f"WalletRepo | Invalid group '{group}' requested")
            return 0
        except SQLAlchemyError:
            log.exception(f"WalletRepo | Error getting {group}/{key}")
            raise

    async def add_resource(self, char_id: int, group: ResourceTypeGroup, key: str, amount: int) -> int:
        """Добавляет ресурс."""
        try:
            wallet = await self.get_wallet(char_id)
            if not hasattr(wallet, group):
                raise ValueError(f"Invalid resource group: {group}")

            # Копируем словарь для SQLAlchemy (чтобы он увидел изменения)
            current_data = dict(getattr(wallet, group, {}) or {})
            new_total = current_data.get(key, 0) + amount
            current_data[key] = new_total

            setattr(wallet, group, current_data)

            log.info(f"WalletRepo | +{amount} {key} -> {new_total} (Group: {group}) for {char_id}")
            return new_total
        except SQLAlchemyError:
            log.exception(f"WalletRepo | Error adding {group}/{key}")
            raise

    async def remove_resource(self, char_id: int, group: ResourceTypeGroup, key: str, amount: int) -> bool:
        """Списывает ресурс."""
        try:
            wallet = await self.get_wallet(char_id)
            if not hasattr(wallet, group):
                raise ValueError(f"Invalid resource group: {group}")

            current_data = dict(getattr(wallet, group, {}) or {})
            current_amount = current_data.get(key, 0)

            if current_amount < amount:
                return False

            new_amount = current_amount - amount
            if new_amount <= 0:
                if key in current_data:
                    del current_data[key]
            else:
                current_data[key] = new_amount

            setattr(wallet, group, current_data)
            log.info(f"WalletRepo | -{amount} {key} -> {new_amount} (Group: {group}) for {char_id}")
            return True
        except SQLAlchemyError:
            log.exception(f"WalletRepo | Error removing {group}/{key}")
            raise
