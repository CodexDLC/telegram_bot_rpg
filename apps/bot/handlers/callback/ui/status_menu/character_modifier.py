from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from apps.bot.resources.keyboards.status_callback import StatusModifierCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.common.core.container import AppContainer

router = Router(name="character_modifier_menu")


@router.callback_query(StatusModifierCallback.filter(F.level == "group"), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_modifier_group_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    callback_data: StatusModifierCallback,
    session: AsyncSession,
    container: AppContainer,
) -> None:
    """Показывает список модификаторов в группе."""
    if not call.from_user:
        return

    await call.answer()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key

    log.info(f"ModifierMenu | event=group_selected user_id={user_id} char_id={char_id} group='{key}'")

    state_data = await state.get_data()

    orchestrator = container.get_status_bot_orchestrator(session)

    result = await orchestrator.get_modifier_view(
        char_id=char_id, level="group", key=key, state_data=state_data, bot=bot
    )

    if result.content and (coords := orchestrator.get_content_coords(state_data)):
        await bot.edit_message_text(
            chat_id=coords.chat_id,
            message_id=coords.message_id,
            text=result.content.text,
            reply_markup=result.content.kb,
            parse_mode="HTML",
        )
        await state.update_data(group_key=key)
        log.debug(f"UIRender | component=modifier_group status=success user_id={user_id} group='{key}'")
    else:
        log.error(f"ModifierMenu | status=failed reason='No content or coords' char_id={char_id}")
        await Err.generic_error(call)


@router.callback_query(StatusModifierCallback.filter(F.level == "detail"), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_modifier_detail_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    callback_data: StatusModifierCallback,
    session: AsyncSession,
    container: AppContainer,
) -> None:
    """Показывает детали конкретного модификатора."""
    if not call.from_user:
        return

    await call.answer()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key

    log.info(f"ModifierMenu | event=detail_selected user_id={user_id} char_id={char_id} modifier='{key}'")

    state_data = await state.get_data()

    orchestrator = container.get_status_bot_orchestrator(session)

    result = await orchestrator.get_modifier_view(
        char_id=char_id, level="detail", key=key, state_data=state_data, bot=bot
    )

    if result.content and (coords := orchestrator.get_content_coords(state_data)):
        await bot.edit_message_text(
            chat_id=coords.chat_id,
            message_id=coords.message_id,
            text=result.content.text,
            reply_markup=result.content.kb,
            parse_mode="HTML",
        )
        log.debug(f"UIRender | component=modifier_detail status=success user_id={user_id} modifier='{key}'")
    else:
        log.error(f"ModifierMenu | status=failed reason='No content or coords' char_id={char_id}")
        await Err.generic_error(call)
