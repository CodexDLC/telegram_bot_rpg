# app/resources/schemas_dto/user_dto.py

from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserUpsertDTO(BaseModel):
    """
    DTO для 'ввода' (создания/обновления).
    Содержит только то, что мы получаем от Telegram API.
    """
    telegram_id: int
    first_name: str
    username: Optional[str]
    last_name: Optional[str]
    language_code: Optional[str]
    is_premium: bool



class UserDTO(UserUpsertDTO):
    """
    DTO для 'вывода' (чтения из БД).
    Содержит все поля из UserUpsertDTO + поля, генерируемые БД.
    """
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)