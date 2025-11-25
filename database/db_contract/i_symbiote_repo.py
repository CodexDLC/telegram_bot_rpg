from abc import ABC, abstractmethod

from database.model_orm.symbiote import CharacterSymbiote


class ISymbioteRepo(ABC):
    """
    Интерфейс репозитория для управления сущностью Симбиота (CharacterSymbiote).
    """

    @abstractmethod
    async def get_symbiote(self, character_id: int) -> CharacterSymbiote | None:
        """Получает запись симбиота по ID персонажа."""
        pass

    @abstractmethod
    async def update_name(self, character_id: int, new_name: str) -> None:
        """Обновляет имя Симбиота (например, после квеста на именование)."""
        pass

    @abstractmethod
    async def set_gift(self, character_id: int, gift_id: str) -> None:
        """Устанавливает выбранный Дар (Gift)."""
        pass

    @abstractmethod
    async def update_progress(self, character_id: int, new_xp: int, new_rank: int) -> None:
        """
        Обновляет опыт и ранг Симбиота.
        Используется после того, как сервис посчитал новый опыт и проверил левел-ап.
        """
        pass
