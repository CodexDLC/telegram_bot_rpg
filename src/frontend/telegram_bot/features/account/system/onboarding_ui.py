from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.frontend.telegram_bot.base.view_dto import ViewResultDTO
from src.frontend.telegram_bot.features.account.resources.keyboards.account_callbacks import OnboardingCallback
from src.frontend.telegram_bot.features.commands.resources.keyboards.commands_callbacks import SystemCallback
from src.shared.schemas.onboarding import OnboardingUIPayloadDTO


class OnboardingUI:
    """
    UI-сервис для Onboarding.
    Динамически рендерит данные от backend.
    """

    def render_menu(self) -> ViewResultDTO:
        """
        Верхнее сообщение (menu): заголовок + Logout.
        """
        text = "🎭 <b>Создание персонажа</b>"
        kb = self._kb_menu()
        return ViewResultDTO(text=text, kb=kb)

    def render_step(self, payload: OnboardingUIPayloadDTO) -> ViewResultDTO:
        """
        Рендер шага онбординга.
        Backend присылает title, description, buttons — просто отображаем.
        """
        text = self._format_step(payload)
        kb = self._build_buttons(payload.buttons) if payload.buttons else None
        return ViewResultDTO(text=text, kb=kb)

    def _format_step(self, payload: OnboardingUIPayloadDTO) -> str:
        """
        Форматирование текста шага.
        """
        lines = [
            f"<b>{payload.title}</b>",
            "",
            payload.description,
        ]

        if payload.error:
            lines.insert(0, f"⚠️ {payload.error}\n")

        return "\n".join(lines)

    def _build_buttons(self, buttons: list) -> InlineKeyboardMarkup:
        """
        Динамическая сборка клавиатуры из buttons[].
        """
        kb = InlineKeyboardBuilder()

        for btn in buttons:
            cb = OnboardingCallback(action=btn.action, value=btn.value).pack()
            kb.button(text=btn.text, callback_data=cb)

        kb.adjust(2)
        return kb.as_markup()

    def _kb_menu(self) -> InlineKeyboardMarkup:
        """
        Клавиатура menu: только Logout.
        """
        kb = InlineKeyboardBuilder()
        kb.button(
            text="🚪 Выйти",
            callback_data=SystemCallback(action="logout").pack(),
        )
        return kb.as_markup()
