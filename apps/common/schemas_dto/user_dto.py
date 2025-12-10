"""
Модуль содержит DTO (Data Transfer Objects) для работы с данными пользователя.

Определяет структуры данных для создания/обновления пользователя
(`UserUpsertDTO`) и для чтения данных пользователя из базы данных (`UserDTO`),
включая информацию, получаемую от Telegram API, и временные метки.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserUpsertDTO(BaseModel):
    """
    DTO для создания или обновления пользователя.
    Содержит поля, получаемые от Telegram API.
    """

    telegram_id: int  # Уникальный идентификатор пользователя в Telegram.
    first_name: str  # Имя пользователя в Telegram.
    username: str | None  # Опциональное имя пользователя (никнейм) в Telegram.
    last_name: str | None  # Опциональная фамилия пользователя в Telegram.
    language_code: str | None  # Опциональный код языка пользователя (например, "ru", "en").
    is_premium: bool  # Флаг, указывающий, является ли пользователь Premium-подписчиком Telegram.


class UserDTO(UserUpsertDTO):
    """
    DTO для чтения данных пользователя из базы данных.
    Включает поля из `UserUpsertDTO` и временные метки.
    """

    created_at: datetime  # Дата и время создания записи пользователя в БД.
    updated_at: datetime  # Дата и время последнего обновления записи пользователя в БД.

    model_config = ConfigDict(from_attributes=True)
