# app/services/ui_service/command_service.py
from aiogram.types import User
from loguru import logger as log

from app.resources.schemas_dto.user_dto import UserUpsertDTO
from database.repositories.ORM.users_repo_orm import UsersRepoORM
from database.session import get_async_session


class CommandService:
    """
    Сервис для обработки базовых команд, таких как /start.

    Инкапсулирует логику, связанную с обработкой данных пользователя
    и взаимодействием с БД при первом контакте пользователя с ботом.
    """

    def __init__(self, user: User) -> None:
        """
        Инициализирует сервис на основе данных пользователя Telegram.

        Args:
            user (User): Объект пользователя, полученный от aiogram.
        """
        self.user_dto = UserUpsertDTO(
            telegram_id=user.id,
            first_name=user.first_name,
            username=user.username,
            last_name=user.last_name,
            language_code=user.language_code,
            is_premium=bool(user.is_premium),
        )
        log.debug(f"Инициализирован {self.__class__.__name__} для user_id={user.id}.")
        log.debug(f"Данные пользователя: {self.user_dto.model_dump_json()}")

    async def create_user_in_db(self) -> None:
        """
        Создает или обновляет запись о пользователе в базе данных (UPSERT).

        Если пользователь с таким `telegram_id` уже существует, его данные
        будут обновлены. Если нет — будет создана новая запись.
        Использует собственную сессию для выполнения этой изолированной операции.

        Returns:
            None
        """
        log.info(f"Запрос на создание/обновление пользователя с telegram_id={self.user_dto.telegram_id}.")
        async with get_async_session() as session:
            user_repo = UsersRepoORM(session)
            try:
                await user_repo.upsert_user(self.user_dto)
                log.info(f"Пользователь {self.user_dto.telegram_id} успешно создан/обновлен в БД.")
            except Exception as e:
                log.exception(f"Ошибка при выполнении upsert для пользователя {self.user_dto.telegram_id}: {e}")
                await session.rollback()
                # Пробрасываем исключение дальше, чтобы его можно было обработать в хэндлере
                raise
