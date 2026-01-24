from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.common.schemas_dto.onboarding_dto import OnboardingStepEnum, OnboardingViewDTO
from game_client.bot.resources.keyboards.callback_data import OnboardingCallback
from game_client.bot.resources.texts.buttons_callback import Buttons
from game_client.bot.ui_service.helpers_ui.dto.ui_common_dto import ViewResultDTO


class OnboardingUIService:
    """
    UI-сервис для онбординга.
    Превращает OnboardingViewDTO (step, draft) в ViewResultDTO (text, kb).
    """

    def render(self, dto: OnboardingViewDTO) -> ViewResultDTO:
        """
        Главный метод рендеринга.
        """
        text = ""
        kb = None

        if dto.error:
            text += f"⚠️ <b>Ошибка:</b> {dto.error}\n\n"

        if dto.step == OnboardingStepEnum.WELCOME:
            text += "Добро пожаловать в мир RPG! Давайте создадим вашего персонажа.\n\nНажмите кнопку, чтобы начать."
            kb = self._get_welcome_kb()

        elif dto.step == OnboardingStepEnum.NAME:
            text += "Как будут звать вашего героя?\n\n<i>Введите имя сообщением:</i>"
            kb = None  # Клавиатура не нужна, ждем текст

        elif dto.step == OnboardingStepEnum.GENDER:
            text += f"Приятно познакомиться, <b>{dto.draft.name}</b>!\n\nВыберите пол вашего персонажа:"
            kb = self._get_gender_kb()

        elif dto.step == OnboardingStepEnum.CONFIRM:
            text += (
                f"Проверьте данные:\n\n"
                f"👤 Имя: <b>{dto.draft.name}</b>\n"
                f"⚧ Пол: <b>{Buttons.GENDER.get(str(dto.draft.gender), dto.draft.gender)}</b>\n\n"
                f"Всё верно?"
            )
            kb = self._get_confirm_kb()

        return ViewResultDTO(text=text, kb=kb)

    def _get_welcome_kb(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="🚀 Начать создание", callback_data=OnboardingCallback(action="start").pack())
        return builder.as_markup()

    def _get_gender_kb(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text=Buttons.GENDER["male"], callback_data=OnboardingCallback(action="set_gender", value="male").pack()
        )
        builder.button(
            text=Buttons.GENDER["female"], callback_data=OnboardingCallback(action="set_gender", value="female").pack()
        )
        builder.adjust(2)
        return builder.as_markup()

    def _get_confirm_kb(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Открыть глаза", callback_data=OnboardingCallback(action="finalize").pack())
        # Можно добавить кнопку "Назад" или "Сбросить", если нужно
        return builder.as_markup()
