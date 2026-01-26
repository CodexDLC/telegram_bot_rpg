import contextlib

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User

from common.schemas.enums import CoreDomain
from game_client.telegram_bot.core.container import BotContainer
from game_client.telegram_bot.features.account.resources.keyboards.account_callbacks import OnboardingCallback
from game_client.telegram_bot.features.account.system.onboarding_orchestrator import OnboardingOrchestrator
from game_client.telegram_bot.services.director.director import GameDirector
from game_client.telegram_bot.services.sender.view_sender import ViewSender

router = Router(name="onboarding_handlers")


@router.callback_query(OnboardingCallback.filter(), StateFilter(CoreDomain.ONBOARDING))
async def on_onboarding_callback(
    call: CallbackQuery,
    callback_data: OnboardingCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    await call.answer()

    if not call.bot:
        return

    client = container.account
    orchestrator = OnboardingOrchestrator(client)

    director = GameDirector(container, state)
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_onboarding_action(user, callback_data.action, callback_data.value)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)


@router.message(F.text, StateFilter(CoreDomain.ONBOARDING))
async def on_onboarding_text(
    message: Message,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    if not message.bot or not message.text:
        return

    with contextlib.suppress(Exception):
        await message.delete()

    client = container.account
    orchestrator = OnboardingOrchestrator(client)

    director = GameDirector(container, state)
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_onboarding_text(user, message.text)

    state_data = await state.get_data()
    sender = ViewSender(bot=message.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)
