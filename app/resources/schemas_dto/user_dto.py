# app/resources/schemas_dto/user_dto.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserUpsertDTO(BaseModel):
    """
    DTO для 'ввода' (создания/обновления).
    Содержит только то, что мы получаем от Telegram API.
    """

    telegram_id: int
    first_name: str
    username: str | None
    last_name: str | None
    language_code: str | None
    is_premium: bool


class UserDTO(UserUpsertDTO):
    """
    DTO для 'вывода' (чтения из БД).
    Содержит все поля из UserUpsertDTO + поля, генерируемые БД.
    """

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
