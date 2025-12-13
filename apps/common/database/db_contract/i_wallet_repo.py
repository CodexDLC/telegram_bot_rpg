from abc import ABC, abstractmethod
from typing import Literal

# ✅ ОБНОВЛЕНО: Только 3 допустимых группы
ResourceTypeGroup = Literal["currency", "resources", "components"]


class IWalletRepo(ABC):
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
        group: ResourceTypeGroup,  # Используем новый Literal
        key: str,
    ) -> int:
        pass

    @abstractmethod
    async def add_resource(
        self,
        char_id: int,
        group: ResourceTypeGroup,  # Используем новый Literal
        key: str,
        amount: int,
    ) -> int:
        pass

    @abstractmethod
    async def remove_resource(
        self,
        char_id: int,
        group: ResourceTypeGroup,  # Используем новый Literal
        key: str,
        amount: int,
    ) -> bool:
        pass
