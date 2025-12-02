from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.keyboards.status_callback import StatusNavCallback
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY, fsm_clean_core_state
from app.services.ui_service.status_menu.status_service import CharacterMenuUIService

router = Router(name="character_status_menu")


async def show_status_tab_logic(
    call: CallbackQuery, state: FSMContext, bot: Bot, char_id: int, key: str, session: AsyncSession
) -> None:
    """
    Отображает указанную вкладку меню статуса персонажа.
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    log.info(f"StatusMenu | event=show_tab user_id={user_id} char_id={char_id} tab='{key}'")

    state_data = await state.get_data()
    callback_for_service = StatusNavCallback(key=key, char_id=char_id)

    try:
        ui_service = CharacterMenuUIService(callback_data=callback_for_service, state_data=state_data)
    except (ValueError, AttributeError, TypeError) as e:
        log.error(
            f"StatusMenu | status=failed reason='UI service init error' user_id={user_id} error='{e}'", exc_info=True
        )
        await Err.handle_exception(call, "Ошибка при инициализации интерфейса.")
        return

    message_data = ui_service.get_message_content_data()
    chat_id, message_id = None, None

    if message_data:
        chat_id, message_id = message_data
    elif call.message:
        log.warning(f"StatusMenu | reason='message_content not found in FSM, using call.message' user_id={user_id}")
        chat_id = call.message.chat.id

    if not chat_id:
        log.error(f"StatusMenu | status=failed reason='chat_id not determined' user_id={user_id}")
        await Err.handle_exception(call, "Не удалось определить чат для отправки сообщения.")
        return

    character = await ui_service.get_data_service(session)
    if not character:
        log.warning(f"StatusMenu | status=failed reason='character not found' user_id={user_id} char_id={char_id}")
        await Err.handle_exception(call, "Не удалось найти данные персонажа.")
        return

    text, kb = None, None
    try:
        if key == "bio":
            text, kb = ui_service.status_bio_message(character=character)
        elif key == "skills":
            result = ui_service.get_skill_group_view(character=character)
            if result:
                text, kb = result
        elif key == "stats":
            result = ui_service.get_modifier_group_view(character=character)
            if result:
                text, kb = result
        else:
            log.warning(f"StatusMenu | reason='unknown_tab_key' user_id={user_id} char_id={char_id} key='{key}'")
            text, kb = ui_service.status_bio_message(character=character)

    except (ValueError, AttributeError, TypeError, KeyError) as e:
        log.error(
            f"StatusMenu | status=failed reason='UI generation error' user_id={user_id} char_id={char_id} tab='{key}' error='{e}'",
            exc_info=True,
        )
        await Err.handle_exception(call, f"Ошибка при создании вкладки '{key}'.")
        return

    if not text or not kb:
        log.error(
            f"StatusMenu | status=failed reason='text or kb empty' user_id={user_id} char_id={char_id} tab='{key}'"
        )
        await Err.handle_exception(call, f"Ошибка при создании вкладки '{key}'.")
        return

    try:
        if message_id is None:
            log.debug(f"UIRender | component=status_menu action=create_new user_id={user_id}")
            msg = await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=kb)
            new_content = {"chat_id": msg.chat.id, "message_id": msg.message_id}
            current_data = await state.get_data()
            session_context = current_data.get(FSM_CONTEXT_KEY, {})
            session_context["message_content"] = new_content
            await state.update_data({FSM_CONTEXT_KEY: session_context})
            log.info(f"UIRender | component=status_menu status=created msg_id={msg.message_id} user_id={user_id}")
        else:
            log.debug(f"UIRender | component=status_menu action=edit_existing msg_id={message_id} user_id={user_id}")
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=kb
            )
        log.info(f"UIRender | component=status_menu status=success user_id={user_id} char_id={char_id} tab='{key}'")

    except TelegramAPIError as e:
        log.error(
            f"UIRender | component=status_menu status=failed user_id={user_id} char_id={char_id} tab='{key}' error='{e}'",
            exc_info=True,
        )


@router.callback_query(StatusNavCallback.filter())
async def status_menu_router_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusNavCallback, session: AsyncSession
) -> None:
    """
    Главный роутер для навигации по вкладкам меню статуса персонажа.
    """
    if not call.from_user:
        return

    key = callback_data.key
    char_id = callback_data.char_id
    user_id = call.from_user.id

    log.info(f"StatusMenuRouter | event=callback user_id={user_id} char_id={char_id} key='{key}'")
    await call.answer()

    try:
        await fsm_clean_core_state(state=state, event_source=call)
        log.debug(f"FSM | action=clean_core_state user_id={user_id} char_id={char_id}")
    except (ValueError, AttributeError, TypeError, KeyError) as e:
        log.error(
            f"StatusMenuRouter | status=failed reason='FSM clean error' user_id={user_id} error='{e}'", exc_info=True
        )
        await Err.handle_exception(call, "Ошибка при обновлении состояния.")
        return

    await show_status_tab_logic(call=call, state=state, bot=bot, char_id=char_id, key=key, session=session)
