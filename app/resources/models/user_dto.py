# app/resources/models/user_dto.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True, slots=True)
class UserUpsertDTO:
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


@dataclass(frozen=True, slots=True)
class UserDTO(UserUpsertDTO):
    """
    DTO для 'вывода' (чтения из БД).
    Содержит все поля из UserUpsertDTO + поля, генерируемые БД.
    """
    created_at: str
    updated_at: str