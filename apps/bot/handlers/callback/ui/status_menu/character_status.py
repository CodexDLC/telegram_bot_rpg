from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.keyboards.status_callback import StatusNavCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import fsm_clean_core_state
from apps.common.core.container import AppContainer

router = Router(name="character_status_menu")


async def show_status_tab_logic(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    char_id: int,
    key: str,
    session: AsyncSession,
    container: AppContainer | None = None,
) -> None:
    """
    Отображает указанную вкладку меню статуса персонажа.
    Временный мост. Вызывается из лобби.
    """
    if not call.from_user:
        return

    user_id = call.from_user.id
    log.info(f"StatusMenu | event=show_tab user_id={user_id} char_id={char_id} tab='{key}'")

    if not container:
        container = AppContainer()  # Fallback, если не передан

    orchestrator = container.get_status_bot_orchestrator(session)
    state_data = await state.get_data()

    # Mypy error: Missing positional argument "bot" in call to "get_status_view" of "StatusBotOrchestrator"
    # Добавляем bot в вызов
    result = await orchestrator.get_status_view(char_id, key, state_data, bot)

    if result.content:
        # Лобби ожидает обновления сообщения, в котором была нажата кнопка
        # Или используем координаты из оркестратора, если они есть
        coords = orchestrator.get_content_coords(state_data)

        chat_id = coords.chat_id if coords else (call.message.chat.id if call.message else None)
        message_id = coords.message_id if coords else (call.message.message_id if call.message else None)

        if chat_id and message_id:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=result.content.text,
                    reply_markup=result.content.kb,
                    parse_mode="HTML",
                )
            except TelegramAPIError as e:
                log.error(f"StatusMenu | status=failed reason='edit_message_text error' user_id={user_id} error='{e}'")
        else:
            log.error(f"StatusMenu | status=failed reason='chat_id or message_id not found' user_id={user_id}")


@router.callback_query(StatusNavCallback.filter())
async def status_menu_router_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    callback_data: StatusNavCallback,
    session: AsyncSession,
    container: AppContainer,
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
    except Exception as e:  # noqa: BLE001
        log.error(f"StatusMenuRouter | status=failed reason='FSM clean error' user_id={user_id} error='{e}'")
        await Err.handle_exception(call, "Ошибка при обновлении состояния.")
        return

    await show_status_tab_logic(
        call=call, state=state, bot=bot, char_id=char_id, key=key, session=session, container=container
    )
