from aiogram.types import User

from app.resources.schemas_dto.user_dto import UserUpsertDTO
from database.repositories import get_user_repo
from database.session import get_async_session


class CommandService:
    """
    Сервис для обработки базовых команд, таких как /start.

    Этот класс инкапсулирует логику, связанную с обработкой данных
    пользователя и взаимодействием с базой данных при первом контакте
    пользователя с ботом.
    """

    def __init__(self, user: User) -> None:
        """
        Инициализирует сервис на основе данных пользователя Telegram.

        Args:
            user (User): Объект пользователя, полученный от aiogram.
        """
        self.telegram_id = user.id
        self.first_name = user.first_name
        self.username = user.username
        self.last_name = user.last_name
        self.language_code = user.language_code
        self.is_premium = bool(user.is_premium)

    async def create_user_in_db(self) -> None:
        """
        Создает или обновляет запись о пользователе в базе данных.

        Использует операцию "upsert" (update or insert), чтобы избежать
        дублирования пользователей. Если пользователь с таким `telegram_id`
        уже существует, его данные будут обновлены. Если нет — будет
        создана новая запись.

        Returns:
            None
        """
        # Создаем DTO (Data Transfer Object) для передачи данных
        # в репозиторий. Это хорошая практика, позволяющая отделить
        # логику сервиса от структуры таблиц БД.
        user_dto = UserUpsertDTO(
            telegram_id=self.telegram_id,
            first_name=self.first_name,
            username=self.username,
            last_name=self.last_name,
            language_code=self.language_code,
            is_premium=self.is_premium
        )

        async with get_async_session() as session:
            user_repo = get_user_repo(session)
            await user_repo.upsert_user(user_dto)
