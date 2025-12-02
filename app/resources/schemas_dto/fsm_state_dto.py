"""
Модуль содержит DTO (Data Transfer Objects) для хранения основного контекста FSM-сессии.

Определяет `SessionDataDTO` — структуру данных, используемую для
сохранения ключевой информации о текущей сессии пользователя
(ID пользователя, ID персонажа, ID сообщений UI и имена).
"""

from pydantic import BaseModel


class SessionDataDTO(BaseModel):
    """
    DTO для хранения основного контекста сессии (Ядра FSM).
    Эти данные сохраняются между различными состояниями FSM.
    """

    user_id: int | None = None  # Идентификатор пользователя Telegram.
    char_id: int | None = None  # Идентификатор активного персонажа пользователя.
    message_menu: dict[str, int] | None = None  # Словарь с chat_id и message_id для сообщения главного меню.
    message_content: dict[str, int] | None = None  # Словарь с chat_id и message_id для контентного сообщения (нижнего).
    char_name: str | None = None  # Имя активного персонажа.
    symbiote_name: str | None = None  # Имя симбиота (NPC-помощника).
