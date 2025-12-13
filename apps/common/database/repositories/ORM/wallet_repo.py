from typing import Literal

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.db_contract.i_wallet_repo import IWalletRepo
from apps.common.database.model_orm.inventory import ResourceWallet


class WalletRepoORM(IWalletRepo):
    """
    Реализация IWalletRepo с использованием SQLAlchemy ORM.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug(f"WalletRepoORM | status=initialized session={session}")

    async def ensure_wallet_exists(self, char_id: int) -> None:
        wallet = await self.session.get(ResourceWallet, char_id)
        if not wallet:
            new_wallet = ResourceWallet(character_id=char_id)
            self.session.add(new_wallet)
            await self.session.flush()
            log.info(f"WalletRepoORM | action=create_wallet char_id={char_id}")

    async def get_wallet(self, char_id: int) -> ResourceWallet:
        await self.ensure_wallet_exists(char_id)
        result = await self.session.execute(select(ResourceWallet).where(ResourceWallet.character_id == char_id))
        return result.scalar_one()

    async def get_resource_amount(
        self,
        char_id: int,
        group: Literal["currency", "resources", "components"],
        key: str,
    ) -> int:
        wallet = await self.get_wallet(char_id)
        target_dict: dict = getattr(wallet, group)
        return target_dict.get(key, 0)

    async def add_resource(
        self,
        char_id: int,
        group: Literal["currency", "resources", "components"],
        key: str,
        amount: int,
    ) -> None:
        wallet = await self.get_wallet(char_id)
        target_dict: dict = getattr(wallet, group)

        current_amount = target_dict.get(key, 0)
        target_dict[key] = current_amount + amount

        wallet.flag_as_modified(group)
        log.debug(f"WalletRepoORM | action=add_resource char_id={char_id} group='{group}' key='{key}' amount={amount}")

    async def remove_resource(
        self,
        char_id: int,
        group: Literal["currency", "resources", "components"],
        key: str,
        amount: int,
    ) -> bool:
        wallet = await self.get_wallet(char_id)
        target_dict: dict = getattr(wallet, group)

        current_amount = target_dict.get(key, 0)
        if current_amount < amount:
            log.warning(
                f"WalletRepo | Insufficient resources for {char_id}: "
                f"has {current_amount} of {key}, but {amount} is required."
            )
            return False

        target_dict[key] = current_amount - amount
        if target_dict[key] == 0:
            del target_dict[key]

        wallet.flag_as_modified(group)
        log.debug(
            f"WalletRepoORM | action=remove_resource char_id={char_id} group='{group}' key='{key}' amount={amount}"
        )
        return True
