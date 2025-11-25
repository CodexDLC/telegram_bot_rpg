# database/repositories/ORM/wallet_repo.py
from typing import Literal

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_contract.i_wallet_repo import IWalletRepo  # <--- Импортируем контракт
from database.model_orm.inventory import ResourceWallet

# Типы групп ресурсов (должны совпадать с полями модели)
ResourceTypeGroup = Literal["currency", "ores", "leathers", "fabrics", "organics", "parts"]


class WalletRepoORM(IWalletRepo):  # <--- Было WalletRepo, стало WalletRepoORM + наследование
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_wallet_exists(self, char_id: int) -> None:
        """Создает кошелек при первом обращении, если его нет."""
        stmt = sqlite_insert(ResourceWallet).values(character_id=char_id).on_conflict_do_nothing()
        await self.session.execute(stmt)

    async def get_wallet(self, char_id: int) -> ResourceWallet:
        """Получает объект кошелька (со всеми JSON-полями)."""
        await self.ensure_wallet_exists(char_id)
        stmt = select(ResourceWallet).where(ResourceWallet.character_id == char_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_resource_amount(self, char_id: int, group: ResourceTypeGroup, key: str) -> int:
        """Возвращает количество конкретного ресурса."""
        wallet = await self.get_wallet(char_id)
        group_data = getattr(wallet, group, {})
        return group_data.get(key, 0)

    async def add_resource(self, char_id: int, group: ResourceTypeGroup, key: str, amount: int) -> int:
        """
        Добавляет ресурс. Возвращает новое количество.
        """
        wallet = await self.get_wallet(char_id)

        # Копируем словарь, чтобы SQLAlchemy увидела изменение
        current_data = getattr(wallet, group, {}).copy()

        new_total = current_data.get(key, 0) + amount
        current_data[key] = new_total

        setattr(wallet, group, current_data)
        return new_total

    async def remove_resource(self, char_id: int, group: ResourceTypeGroup, key: str, amount: int) -> bool:
        """
        Списывает ресурс.
        Возвращает True, если списание успешно.
        Возвращает False, если не хватает ресурсов.
        """
        wallet = await self.get_wallet(char_id)
        current_data = getattr(wallet, group, {}).copy()

        current_amount = current_data.get(key, 0)

        if current_amount < amount:
            log.warning(f"Char {char_id}: Не хватает ресурса '{key}' ({current_amount} < {amount})")
            return False

        # Списываем
        current_data[key] = current_amount - amount

        # Если стало 0, можно удалить ключ для экономии места (опционально)
        if current_data[key] <= 0:
            del current_data[key]

        setattr(wallet, group, current_data)
        return True
