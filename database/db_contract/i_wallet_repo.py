from abc import ABC, abstractmethod
from typing import Literal

from database.model_orm.inventory import ResourceWallet

ResourceTypeGroup = Literal["currency", "ores", "leathers", "fabrics", "organics", "parts"]


class IWalletRepo(ABC):
    """
    Интерфейс для работы с Кошельком Ресурсов (`ResourceWallet`).

    Определяет контракт для управления ресурсами персонажа,
    включая создание кошелька, получение количества ресурсов,
    а также добавление и удаление ресурсов.
    """

    @abstractmethod
    async def ensure_wallet_exists(self, char_id: int) -> None:
        """
        Создает кошелек для персонажа, если он еще не существует.

        Args:
            char_id: Идентификатор персонажа.
        """
        pass

    @abstractmethod
    async def get_wallet(self, char_id: int) -> ResourceWallet:
        """
        Возвращает полный объект кошелька для указанного персонажа.

        Args:
            char_id: Идентификатор персонажа.

        Returns:
            Объект `ResourceWallet`.
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass
