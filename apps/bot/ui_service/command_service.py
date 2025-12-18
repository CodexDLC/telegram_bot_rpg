# app/services/ui_service/command_service.py
from aiogram.types import User
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.database.repositories import UsersRepoORM
from apps.common.schemas_dto import UserUpsertDTO


class CommandService:
    """
    Сервис для обработки базовых команд, таких как /start.
    """

    def __init__(self, user: User) -> None:
        self.user_dto = UserUpsertDTO(
            telegram_id=user.id,
            first_name=user.first_name,
            username=user.username,
            last_name=user.last_name,
            language_code=user.language_code,
            is_premium=bool(user.is_premium),
        )
        log.debug(f"Инициализирован {self.__class__.__name__} для user_id={user.id}.")

    async def create_user_in_db(self, session: AsyncSession) -> None:
        """
        Создает или обновляет запись о пользователе в базе данных (UPSERT).
        Управление транзакцией (commit/rollback) делегировано middleware.
        """
        log.info(f"Запрос на создание/обновление пользователя с telegram_id={self.user_dto.telegram_id}.")
        user_repo = UsersRepoORM(session)
        await user_repo.upsert_user(self.user_dto)
        log.info(f"Пользователь {self.user_dto.telegram_id} успешно создан/обновлен в БД (ожидает коммита).")
