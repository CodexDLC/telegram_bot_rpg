from typing import Any

from game_client.telegram_bot.common.resources.constants import FSM_CONTEXT_KEY


class BaseUIService:
    """
    Базовый сервис доступа к UI-контексту в FSM.
    Отвечает только за чтение/парсинг структуры данных UI (координаты сообщений).
    """

    def __init__(self, state_data: dict[str, Any], char_id: int | None = None):
        """
        :param state_data: Сырой словарь данных из FSM (state.get_data())
        :param char_id: ID персонажа (для логов и контекста), опционально.
        """
        self.state_data = state_data

        # Пытаемся достать char_id из контекста, если не передали явно
        session_context = self.state_data.get(FSM_CONTEXT_KEY, {})
        self.char_id = char_id or session_context.get("char_id")

    def get_message_content_data(self) -> tuple[int, int] | None:
        """
        Возвращает (chat_id, message_id) основного сообщения (Content).
        """
        session_context = self.state_data.get(FSM_CONTEXT_KEY, {})
        message_content = session_context.get("message_content")

        if not isinstance(message_content, dict):
            return None

        chat_id = message_content.get("chat_id")
        message_id = message_content.get("message_id")

        if isinstance(chat_id, int) and isinstance(message_id, int):
            return chat_id, message_id
        return None

    def get_message_menu_data(self) -> tuple[int, int] | None:
        """
        Возвращает (chat_id, message_id) сообщения меню (Menu/Log).
        """
        session_context = self.state_data.get(FSM_CONTEXT_KEY, {})
        message_menu = session_context.get("message_menu")

        if not isinstance(message_menu, dict):
            return None

        chat_id = message_menu.get("chat_id")
        message_id = message_menu.get("message_id")

        if isinstance(chat_id, int) and isinstance(message_id, int):
            return chat_id, message_id
        return None
