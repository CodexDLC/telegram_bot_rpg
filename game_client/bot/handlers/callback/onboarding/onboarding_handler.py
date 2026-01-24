import contextlib

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from game_client.bot.bot_container import BotContainer
from game_client.bot.resources.fsm_states.states import BotState
from game_client.bot.resources.keyboards.callback_data import OnboardingCallback
from game_client.bot.ui_service.game_director.director import GameDirector
from game_client.bot.ui_service.view_sender import ViewSender

router = Router(name="onboarding_router")


async def on_onboarding_action(
    call: CallbackQuery,
    callback_data: OnboardingCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    bot_container: BotContainer,
) -> None:
    """
    Единая точка входа для всех действий онбординга.
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    log.info(f"Onboarding | action={callback_data.action} value={callback_data.value} user_id={user_id}")
    await call.answer()

    state_data = await state.get_data()
    director = GameDirector(container=bot_container, state=state, session=session)
    orchestrator = bot_container.get_onboarding_bot_orchestrator()
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_callback(call.from_user, callback_data.action, callback_data.value)

    if view_dto:
        sender = ViewSender(bot, state, state_data, user_id)
        await sender.send(view_dto)


@router.callback_query(OnboardingCallback.filter())
async def onboarding_callback_handler(
    call: CallbackQuery,
    callback_data: OnboardingCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    bot_container: BotContainer,
) -> None:
    await on_onboarding_action(call, callback_data, state, bot, session, bot_container)


@router.message(BotState.onboarding, F.text)
async def onboarding_text_handler(
    message: Message,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    bot_container: BotContainer,
) -> None:
    if not message.from_user:
        return

    user_id = message.from_user.id
    text = message.text

    if not text:
        # Игнорируем сообщения без текста (хотя фильтр F.text должен был их отсеять, но для mypy полезно)
        return

    log.info(f"Onboarding | input_text='{text}' user_id={user_id}")

    # Удаляем сообщение пользователя, чтобы не засорять чат
    with contextlib.suppress(Exception):
        await message.delete()

    state_data = await state.get_data()
    director = GameDirector(container=bot_container, state=state, session=session)
    orchestrator = bot_container.get_onboarding_bot_orchestrator()
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_text_input(message.from_user, text)

    if view_dto:
        sender = ViewSender(bot, state, state_data, user_id)
        await sender.send(view_dto)
