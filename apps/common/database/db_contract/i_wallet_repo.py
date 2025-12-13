from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from apps.common.database.model_orm.inventory import ResourceWallet


class IWalletRepo(ABC):
    """
    Интерфейс для управления кошельком ресурсов персонажа.
    """

    @abstractmethod
    async def ensure_wallet_exists(self, char_id: int) -> None:
        pass

    @abstractmethod
    async def get_wallet(self, char_id: int) -> "ResourceWallet":
        pass

    @abstractmethod
    async def get_resource_amount(
        self,
        char_id: int,
        group: Literal["currency", "resources", "components"],
        key: str,
    ) -> int:
        """
        Возвращает количество указанного ресурса в кошельке.
        """
        pass

    @abstractmethod
    async def add_resource(
        self,
        char_id: int,
        group: Literal["currency", "resources", "components"],
        key: str,
        amount: int,
    ) -> None:
        pass

    @abstractmethod
    async def remove_resource(
        self,
        char_id: int,
        group: Literal["currency", "resources", "components"],
        key: str,
        amount: int,
    ) -> bool:
        pass
