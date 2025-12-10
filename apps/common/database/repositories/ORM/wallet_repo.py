from typing import Literal

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.db_contract.i_wallet_repo import IWalletRepo
from apps.common.database.model_orm.inventory import ResourceWallet

ResourceTypeGroup = Literal["currency", "ores", "leathers", "fabrics", "organics", "parts"]


class WalletRepoORM(IWalletRepo):
    """
    ORM-реализация репозитория для управления Кошельком Ресурсов (`ResourceWallet`).

    Предоставляет методы для создания, получения, добавления и удаления
    ресурсов персонажа, используя SQLAlchemy ORM.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует WalletRepoORM.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session
        log.debug(f"WalletRepoORM | status=initialized session={session}")

    async def ensure_wallet_exists(self, char_id: int) -> None:
        """
        Создает запись кошелька для персонажа, если она еще не существует.

        Использует `on_conflict_do_nothing` для атомарности.

        Args:
            char_id: Идентификатор персонажа.
        """
        log.debug(f"WalletRepoORM | action=ensure_wallet_exists char_id={char_id}")
        stmt = sqlite_insert(ResourceWallet).values(character_id=char_id).on_conflict_do_nothing()
        try:
            await self.session.execute(stmt)
            log.debug(f"WalletRepoORM | action=ensure_wallet_exists status=success char_id={char_id}")
        except SQLAlchemyError:
            log.exception(f"WalletRepoORM | action=ensure_wallet_exists status=failed char_id={char_id}")
            raise

    async def get_wallet(self, char_id: int) -> ResourceWallet:
        """
        Получает объект кошелька (`ResourceWallet`) для указанного персонажа.

        Если кошелек не существует, он будет создан.

        Args:
            char_id: Идентификатор персонажа.

        Returns:
            Объект `ResourceWallet`.
        """
        log.debug(f"WalletRepoORM | action=get_wallet char_id={char_id}")
        await self.ensure_wallet_exists(char_id)
        stmt = select(ResourceWallet).where(ResourceWallet.character_id == char_id)
        try:
            result = await self.session.execute(stmt)
            wallet = result.scalar_one()
            log.debug(f"WalletRepoORM | action=get_wallet status=success char_id={char_id}")
            return wallet
        except SQLAlchemyError:
            log.exception(f"WalletRepoORM | action=get_wallet status=failed char_id={char_id}")
            raise

    async def get_resource_amount(self, char_id: int, group: ResourceTypeGroup, key: str) -> int:
        """
        Возвращает количество конкретного ресурса из кошелька персонажа.

        Args:
            char_id: Идентификатор персонажа.
            group: Группа ресурсов (например, "currency", "ores").
            key: Ключ ресурса (например, "dust", "iron_ore").

        Returns:
            Количество ресурса.
        """
        log.debug(f"WalletRepoORM | action=get_resource_amount char_id={char_id} group='{group}' key='{key}'")
        try:
            wallet = await self.get_wallet(char_id)
            group_data = getattr(wallet, group, {})
            amount = group_data.get(key, 0)
            log.debug(
                f"WalletRepoORM | action=get_resource_amount status=success char_id={char_id} key='{key}' amount={amount}"
            )
            return amount
        except SQLAlchemyError:
            log.exception(
                f"WalletRepoORM | action=get_resource_amount status=failed char_id={char_id} group='{group}' key='{key}'"
            )
            raise
        except AttributeError:
            log.error(
                f"WalletRepoORM | action=get_resource_amount status=failed reason='Invalid group' char_id={char_id} group='{group}'"
            )
            return 0

    async def add_resource(self, char_id: int, group: ResourceTypeGroup, key: str, amount: int) -> int:
        """
        Добавляет указанное количество ресурса в кошелек персонажа.

        Args:
            char_id: Идентификатор персонажа.
            group: Группа ресурсов.
            key: Ключ ресурса.
            amount: Количество для добавления.

        Returns:
            Новое итоговое количество ресурса.
        """
        log.debug(f"WalletRepoORM | action=add_resource char_id={char_id} group='{group}' key='{key}' amount={amount}")
        try:
            wallet = await self.get_wallet(char_id)
            current_data = getattr(wallet, group, {}).copy()
            new_total = current_data.get(key, 0) + amount
            current_data[key] = new_total
            setattr(wallet, group, current_data)
            log.info(
                f"WalletRepoORM | action=add_resource status=success char_id={char_id} key='{key}' new_total={new_total}"
            )
            return new_total
        except SQLAlchemyError:
            log.exception(
                f"WalletRepoORM | action=add_resource status=failed char_id={char_id} group='{group}' key='{key}'"
            )
            raise
        except AttributeError:
            log.error(
                f"WalletRepoORM | action=add_resource status=failed reason='Invalid group' char_id={char_id} group='{group}'"
            )
            raise

    async def remove_resource(self, char_id: int, group: ResourceTypeGroup, key: str, amount: int) -> bool:
        """
        Списывает указанное количество ресурса из кошелька персонажа.

        Args:
            char_id: Идентификатор персонажа.
            group: Группа ресурсов.
            key: Ключ ресурса.
            amount: Количество для списания.

        Returns:
            True, если ресурс успешно списан, иначе False (например, если ресурсов недостаточно).
        """
        log.debug(
            f"WalletRepoORM | action=remove_resource char_id={char_id} group='{group}' key='{key}' amount={amount}"
        )
        try:
            wallet = await self.get_wallet(char_id)
            current_data = getattr(wallet, group, {}).copy()
            current_amount = current_data.get(key, 0)

            if current_amount < amount:
                log.warning(
                    f"WalletRepoORM | action=remove_resource status=failed reason='Insufficient resources' char_id={char_id} key='{key}' current={current_amount} requested={amount}"
                )
                return False

            current_data[key] = current_amount - amount
            if current_data[key] <= 0:
                del current_data[key]

            setattr(wallet, group, current_data)
            log.info(
                f"WalletRepoORM | action=remove_resource status=success char_id={char_id} key='{key}' new_total={current_data.get(key, 0)}"
            )
            return True
        except SQLAlchemyError:
            log.exception(
                f"WalletRepoORM | action=remove_resource status=failed char_id={char_id} group='{group}' key='{key}'"
            )
            raise
        except AttributeError:
            log.error(
                f"WalletRepoORM | action=remove_resource status=failed reason='Invalid group' char_id={char_id} group='{group}'"
            )
            raise
