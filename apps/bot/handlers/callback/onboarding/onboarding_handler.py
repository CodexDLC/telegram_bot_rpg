import contextlib

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import BotState
from apps.bot.resources.keyboards.callback_data import OnboardingCallback
from apps.bot.ui_service.game_director.director import GameDirector
from apps.bot.ui_service.view_sender import ViewSender
from apps.common.core.container import AppContainer

router = Router(name="onboarding_router")


@router.callback_query(OnboardingCallback.filter())
async def on_onboarding_action(
    call: CallbackQuery,
    callback_data: OnboardingCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    container: AppContainer,
):
    """
    Обработка кнопок онбординга.
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    log.info(f"Onboarding | action={callback_data.action} value={callback_data.value} user_id={user_id}")
    await call.answer()

    # 1. Инициализация
    state_data = await state.get_data()
    director = GameDirector(container, state, session)
    orchestrator = container.get_onboarding_bot_orchestrator(session)
    orchestrator.set_director(director)

    # 2. Выполнение действия
    view_dto = await orchestrator.handle_callback(
        user=call.from_user, action=callback_data.action, value=callback_data.value
    )

    # 3. Отправка ответа
    if view_dto:
        sender = ViewSender(bot, state, state_data, user_id)
        await sender.send(view_dto)


@router.message(BotState.onboarding, F.text)
async def on_text_input(
    message: Message,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    container: AppContainer,
):
    """
    Обработка текстового ввода (имя).
    """
    if not message.from_user or not message.text:
        return

    user_id = message.from_user.id
    text = message.text.strip()
    log.info(f"Onboarding | input_text='{text}' user_id={user_id}")

    # Удаляем сообщение пользователя для чистоты чата
    with contextlib.suppress(Exception):
        await message.delete()

    # 1. Инициализация
    state_data = await state.get_data()
    director = GameDirector(container, state, session)
    orchestrator = container.get_onboarding_bot_orchestrator(session)
    orchestrator.set_director(director)

    # 2. Выполнение действия
    view_dto = await orchestrator.handle_text_input(user=message.from_user, text=text)

    # 3. Отправка ответа
    if view_dto:
        sender = ViewSender(bot, state, state_data, user_id)
        await sender.send(view_dto)


# --- Entry Point (вызывается из Lobby/Login) ---
# Этот метод больше не нужен как отдельная функция, так как переход
# осуществляется через Director.set_scene(ONBOARDING), который вызывает orchestrator.render().
# Но если где-то остался старый вызов start_onboarding_process, его нужно заменить.
