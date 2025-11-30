# app/services/ui_service/base_service.py
from typing import Any

from loguru import logger as log

from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY


class BaseUIService:
    """
    Базовый сервис, от которого наследуются все UI-сервисы.
    Содержит общую логику, например, для работы с FSM.
    """

    def __init__(self, state_data: dict[str, Any], char_id: int | None = None):
        """
        Инициализирует базовые атрибуты, нужные ВСЕМ сервисам.
        """
        self.state_data = state_data
        session_context = self.state_data.get(FSM_CONTEXT_KEY, {})
        self.char_id = char_id or session_context.get("char_id")
        self.actor_name = session_context.get("symbiote_name", DEFAULT_ACTOR_NAME)
        log.debug(f"Инициализирован BaseUIService для char_id={self.char_id}.")

    def get_message_content_data(self) -> tuple[int, int] | None:
        """
        Извлекает chat_id и message_id из данных состояния FSM.
        """
        session_context = self.state_data.get(FSM_CONTEXT_KEY, {})
        message_content: dict[str, Any] | None = session_context.get("message_content")
        if not isinstance(message_content, dict):  # <--- Проверка, что это словарь
            log.warning(f"В FSM state для char_id={self.char_id} отсутствует 'message_content'.")
            return None

        chat_id = message_content.get("chat_id")
        message_id = message_content.get("message_id")

        if not isinstance(chat_id, int) or not isinstance(message_id, int):
            log.warning(
                f"В 'message_content' для char_id={self.char_id} 'chat_id' или 'message_id' не являются int или отсутствуют."
            )
            return None

        log.debug(f"Извлечены данные сообщения: chat_id={chat_id}, message_id={message_id}.")
        return chat_id, message_id

    def get_message_menu_data(self) -> tuple[int, int] | None:
        """
        Извлекает chat_id и message_id из 'message_menu'.
        """
        session_context = self.state_data.get(FSM_CONTEXT_KEY, {})
        message_menu = session_context.get("message_menu")
        if not message_menu:
            log.warning(f"В FSM state для char_id={self.char_id} отсутствует 'message_menu'.")
            return None

        chat_id = message_menu.get("chat_id")
        message_id = message_menu.get("message_id")

        if not chat_id or not message_id:
            log.warning(f"В 'message_menu' для char_id={self.char_id} отсутствует 'chat_id' или 'message_id'.")
            return None

        log.debug(f"Извлечены данные МЕНЮ: chat_id={chat_id}, message_id={message_id}.")
        return chat_id, message_id
