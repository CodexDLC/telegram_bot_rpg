from abc import ABC, abstractmethod

from app.resources.schemas_dto.user_dto import UserDTO, UserUpsertDTO


class IUserRepo(ABC):
    """
    Абстрактный базовый класс (интерфейс) для репозитория пользователей.

    Определяет контракт, которому должны следовать все конкретные реализации
    репозиториев пользователей, независимо от используемой базы данных.
    """

    @abstractmethod
    async def upsert_user(self, user_data: UserUpsertDTO) -> None:
        """
        Создает нового пользователя или обновляет данные существующего.

        Реализация этого метода должна обеспечивать атомарность операции:
        если пользователь с указанным `telegram_id` существует, его данные
        (first_name, username и т.д.) обновляются. Если не существует -
        создается новая запись.

        Args:
            user_data: DTO с данными для создания или обновления пользователя.
        """
        pass

    @abstractmethod
    async def get_user(self, telegram_id: int) -> UserDTO | None:
        """
        Находит и возвращает одного пользователя по его `telegram_id`.

        Args:
            telegram_id: Уникальный идентификатор пользователя в Telegram.

        Returns:
            DTO `UserDTO` с полными данными пользователя, если он найден,
            в противном случае - None.
        """
        pass

    @abstractmethod
    async def get_users(self) -> list[UserDTO]:
        """
        Возвращает список всех пользователей в системе.

        Этот метод может использоваться для административных задач,
        рассылок или отладки.

        Returns:
            Список DTO `UserDTO` всех пользователей.
            Если пользователей нет, возвращает пустой список.
        """
        pass
