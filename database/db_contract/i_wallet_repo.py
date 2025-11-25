from abc import ABC, abstractmethod
from typing import Literal

from database.model_orm.inventory import ResourceWallet

# Типы групп (дублируем или импортируем из конфига, чтобы контракт знал о типах)
ResourceTypeGroup = Literal["currency", "ores", "leathers", "fabrics", "organics", "parts"]


class IWalletRepo(ABC):
    """
    Интерфейс для работы с Кошельком Ресурсов (ResourceWallet).
    """

    @abstractmethod
    async def ensure_wallet_exists(self, char_id: int) -> None:
        """Создает кошелек для персонажа, если он еще не создан."""
        pass

    @abstractmethod
    async def get_wallet(self, char_id: int) -> ResourceWallet:
        """Возвращает полный объект кошелька."""
        pass

    @abstractmethod
    async def get_resource_amount(self, char_id: int, group: ResourceTypeGroup, key: str) -> int:
        """Возвращает количество конкретного ресурса."""
        pass

    @abstractmethod
    async def add_resource(self, char_id: int, group: ResourceTypeGroup, key: str, amount: int) -> int:
        """
        Добавляет ресурс. Возвращает новое итоговое количество.
        """
        pass

    @abstractmethod
    async def remove_resource(self, char_id: int, group: ResourceTypeGroup, key: str, amount: int) -> bool:
        """
        Списывает ресурс. Возвращает False, если ресурсов недостаточно.
        """
        pass
