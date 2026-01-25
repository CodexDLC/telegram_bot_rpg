from loguru import logger as log

from game_client.telegram_bot.base.view_dto import UnifiedViewDTO, ViewResultDTO
from game_client.telegram_bot.services.error.ui.keyboards import get_error_keyboard
from game_client.telegram_bot.services.error.ui.texts import ERROR_TEXTS, ErrorKeys


class ErrorBotOrchestrator:
    """
    Оркестратор для обработки ошибок и генерации аварийных экранов.
    """

    def create_error_view(
        self, error_key: ErrorKeys, user_id: int, source: str = "unknown", is_critical: bool = False
    ) -> UnifiedViewDTO:
        """
        Генерирует экран ошибки на основе ключа.
        """
        # 1. Логирование
        log.error(f"ErrorOrchestrator | source={source} user_id={user_id} key={error_key}")

        # 2. Получение текста
        text = ERROR_TEXTS.get(error_key, ERROR_TEXTS[ErrorKeys.UNKNOWN_ERROR])

        # 3. Клавиатура
        if error_key == ErrorKeys.ACCESS_DENIED:
            # Для "чужого интерфейса" кнопка не нужна, это обычно Alert
            return UnifiedViewDTO(alert_text=text)

        kb_builder = get_error_keyboard()
        content_view = ViewResultDTO(text=text, kb=kb_builder.as_markup())

        return UnifiedViewDTO(menu=None, content=content_view, clean_history=is_critical)

    # --- Shortcuts ---

    def view_session_expired(self, user_id: int, source: str) -> UnifiedViewDTO:
        return self.create_error_view(ErrorKeys.SESSION_EXPIRED, user_id, source, is_critical=True)

    def view_char_not_found(self, user_id: int, source: str) -> UnifiedViewDTO:
        return self.create_error_view(ErrorKeys.CHAR_NOT_FOUND, user_id, source, is_critical=True)

    def view_backend_error(self, user_id: int, source: str) -> UnifiedViewDTO:
        return self.create_error_view(ErrorKeys.BACKEND_ERROR, user_id, source, is_critical=False)

    def view_access_denied(self, user_id: int, source: str) -> UnifiedViewDTO:
        return self.create_error_view(ErrorKeys.ACCESS_DENIED, user_id, source, is_critical=False)

    def view_generic_error(self, user_id: int, source: str) -> UnifiedViewDTO:
        """
        Отображает общую ошибку (UNKNOWN_ERROR).
        Source используется для логирования причины.
        """
        return self.create_error_view(ErrorKeys.UNKNOWN_ERROR, user_id, source, is_critical=False)
