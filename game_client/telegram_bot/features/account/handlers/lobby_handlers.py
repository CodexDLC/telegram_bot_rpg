from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, User

from common.schemas.enums import CoreDomain
from game_client.telegram_bot.core.container import BotContainer
from game_client.telegram_bot.features.account.resources.keyboards.account_callbacks import LobbyCallback
from game_client.telegram_bot.features.account.system.lobby_orchestrator import LobbyOrchestrator
from game_client.telegram_bot.services.director.director import GameDirector
from game_client.telegram_bot.services.sender.view_sender import ViewSender

router = Router(name="lobby_handlers")


@router.callback_query(LobbyCallback.filter(F.action == "select"), StateFilter(CoreDomain.LOBBY))
async def on_character_select(
    call: CallbackQuery,
    callback_data: LobbyCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    await call.answer()

    if not call.bot or not callback_data.char_id:
        return

    client = container.account
    orchestrator = LobbyOrchestrator(client)

    director = GameDirector(container, state)
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_character_select(user, callback_data.char_id)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)


@router.callback_query(LobbyCallback.filter(F.action == "login"), StateFilter(CoreDomain.LOBBY))
async def on_character_login(
    call: CallbackQuery,
    callback_data: LobbyCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    await call.answer()

    if not call.bot or not callback_data.char_id:
        return

    client = container.account
    orchestrator = LobbyOrchestrator(client)

    director = GameDirector(container, state)
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_character_login(user, callback_data.char_id)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)


@router.callback_query(LobbyCallback.filter(F.action == "create"), StateFilter(CoreDomain.LOBBY))
async def on_character_create(
    call: CallbackQuery,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    await call.answer()

    if not call.bot:
        return

    client = container.account
    orchestrator = LobbyOrchestrator(client)

    director = GameDirector(container, state)
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_character_create(user)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)


@router.callback_query(LobbyCallback.filter(F.action == "delete"), StateFilter(CoreDomain.LOBBY))
async def on_character_delete_request(
    call: CallbackQuery,
    callback_data: LobbyCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    await call.answer()

    if not call.bot or not callback_data.char_id:
        return

    client = container.account
    orchestrator = LobbyOrchestrator(client)

    director = GameDirector(container, state)
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_delete_request(user, callback_data.char_id)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)


@router.callback_query(LobbyCallback.filter(F.action == "delete_confirm"), StateFilter(CoreDomain.LOBBY))
async def on_character_delete_confirm(
    call: CallbackQuery,
    callback_data: LobbyCallback,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    await call.answer()

    if not call.bot or not callback_data.char_id:
        return

    client = container.account
    orchestrator = LobbyOrchestrator(client)

    director = GameDirector(container, state)
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_delete_confirm(user, callback_data.char_id)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)


@router.callback_query(LobbyCallback.filter(F.action == "delete_cancel"), StateFilter(CoreDomain.LOBBY))
async def on_character_delete_cancel(
    call: CallbackQuery,
    state: FSMContext,
    user: User,
    container: BotContainer,
) -> None:
    await call.answer()

    if not call.bot:
        return

    client = container.account
    orchestrator = LobbyOrchestrator(client)

    director = GameDirector(container, state)
    orchestrator.set_director(director)

    view_dto = await orchestrator.handle_lobby_initialize(user)

    state_data = await state.get_data()
    sender = ViewSender(bot=call.bot, state=state, state_data=state_data, user_id=user.id)
    await sender.send(view_dto)
