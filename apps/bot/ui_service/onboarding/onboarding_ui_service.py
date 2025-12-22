from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bot.resources.keyboards.callback_data import OnboardingCallback, ScenarioCallback
from apps.bot.ui_service.onboarding.dto.onboarding_view_dto import OnboardingViewDTO
from apps.bot.ui_service.onboarding.formatters.onboarding_formatter import OnboardingFormatter
from apps.common.schemas_dto.onboarding_dto import OnboardingButtonDTO, OnboardingResponseDTO


class OnboardingUIService:
    """
    UI-сервис (View Layer).
    Единственная задача: превратить DTO от бэкенда в красивый текст и клавиатуру Telegram.
    """

    def render_view(self, dto: OnboardingResponseDTO, context: dict | None = None) -> OnboardingViewDTO:
        """
        Преобразует ответ бэкенда в UI элементы.
        Использует OnboardingFormatter для обработки текста.
        """
        # Делегируем форматирование текста специальному классу
        text = OnboardingFormatter.format_text(dto.text, context)

        builder = InlineKeyboardBuilder()

        for btn in dto.buttons:
            callback_data = self._generate_callback(btn)
            builder.add(InlineKeyboardButton(text=btn.label, callback_data=callback_data))

        # Настраиваем сетку (по 1 кнопке в ряд)
        builder.adjust(1)

        return OnboardingViewDTO(text=text, keyboard=builder.as_markup())

    def _generate_callback(self, btn: OnboardingButtonDTO) -> str:
        """
        Генерирует правильный CallbackData в зависимости от типа кнопки.
        """
        if btn.is_scenario:
            # Переключение на движок сценариев (ScenarioCallback)
            return ScenarioCallback(action="initialize", quest_key=str(btn.value)).pack()

        # Внутренняя навигация онбординга (OnboardingCallback)
        val = str(btn.value) if btn.value is not None else None
        return OnboardingCallback(action=btn.action, value=val).pack()
