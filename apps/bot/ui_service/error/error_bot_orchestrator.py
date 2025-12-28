from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.bot.resources.keyboards.callback_data import StartMenuCallback
from apps.bot.resources.texts.error_messages import ERROR_TEXTS, ErrorKeys
from apps.bot.ui_service.dto.view_dto import UnifiedViewDTO
from apps.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


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

        # Добавляем тех. инфо только если это не штатная ситуация (как access_denied)
        if error_key not in (ErrorKeys.ACCESS_DENIED, ErrorKeys.SESSION_EXPIRED):
            # Можно добавить ID ошибки для саппорта, но пока просто текст
            pass

        # 3. Клавиатура
        kb_builder = InlineKeyboardBuilder()

        if error_key == ErrorKeys.ACCESS_DENIED:
            # Для "чужого интерфейса" кнопка не нужна, это обычно Alert
            # Но UnifiedViewDTO пока не поддерживает Alert-only без контента.
            # Если мы хотим Alert, мы должны вернуть DTO с alert_text.
            return UnifiedViewDTO(alert_text=text)

        # Кнопка Рестарт
        kb_builder.button(text="🔄 В главное меню", callback_data=StartMenuCallback(action="adventure").pack())
        kb_builder.adjust(1)

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
