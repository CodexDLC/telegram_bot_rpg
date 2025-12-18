import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from apps.bot.resources.keyboards.status_callback import StatusModifierCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.bot.ui_service.status_menu.status_modifier_service import CharacterModifierUIService
from apps.common.schemas_dto import SessionDataDTO

router = Router(name="character_modifier_menu")


@router.callback_query(StatusModifierCallback.filter(F.level == "group"), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_modifier_group_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusModifierCallback, session: AsyncSession
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
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    async def run_logic():
        try:
            modifier_service = CharacterModifierUIService(char_id=char_id, key=key, state_data=state_data)
            dto_to_use = await modifier_service.get_aggregated_data(session)

            if not dto_to_use:
                log.warning(f"ModifierMenu | status=failed reason='Aggregated data not found' char_id={char_id}")
                await Err.generic_error(call)
                return None, None, None

            result = modifier_service.status_group_modifier_message(dto_to_use)
            if not result or not result[0] or not result[1]:
                log.error(
                    f"ModifierMenu | status=failed reason='status_group_modifier_message returned empty' char_id={char_id}"
                )
                await Err.generic_error(call)
                return None, None, None

            message_content = modifier_service.get_message_content_data()
            if not message_content:
                log.error(f"ModifierMenu | status=failed reason='message_content not found' char_id={char_id}")
                await Err.message_content_not_found_in_fsm(call=call)
                return None, None, None

            return result[0], result[1], message_content

        except (ValueError, AttributeError, TypeError) as e:
            log.error(
                f"ModifierMenu | status=failed reason='Logic error in group handler' user_id={user_id} error='{e}'",
                exc_info=True,
            )
            await Err.generic_error(call)
            return None, None, None

    results = await asyncio.gather(
        anim_service.animate_loading(duration=1.0, text="📊 <b>Анализ показателей...</b>"),
        run_logic(),
    )

    text, kb, message_content = results[1]
    if text is None:
        return

    chat_id, message_id = message_content
    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="html", reply_markup=kb)
    await state.update_data(group_key=key)
    log.debug(f"UIRender | component=modifier_group status=success user_id={user_id} group='{key}'")


@router.callback_query(StatusModifierCallback.filter(F.level == "detail"), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_modifier_detail_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusModifierCallback, session: AsyncSession
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
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    async def run_logic():
        try:
            group_key = state_data.get("group_key")
            if not group_key:
                log.warning(f"ModifierMenu | status=failed reason='group_key not found in FSM' user_id={user_id}")
                await Err.generic_error(call=call)
                return None, None, None

            modifier_service = CharacterModifierUIService(char_id=char_id, key=key, state_data=state_data)
            dto_to_use = await modifier_service.get_aggregated_data(session)

            if not dto_to_use:
                log.warning(
                    f"ModifierMenu | status=failed reason='Aggregated data not found for detail' char_id={char_id}"
                )
                await Err.generic_error(call=call)
                return None, None, None

            result = modifier_service.status_detail_modifier_message(dto_to_use=dto_to_use, group_key=group_key)
            if not result or not result[0] or not result[1]:
                log.error(
                    f"ModifierMenu | status=failed reason='status_detail_modifier_message returned empty' char_id={char_id}"
                )
                await Err.generic_error(call)
                return None, None, None

            message_content = modifier_service.get_message_content_data()
            if not message_content:
                log.error(
                    f"ModifierMenu | status=failed reason='message_content not found for detail' char_id={char_id}"
                )
                await Err.message_content_not_found_in_fsm(call=call)
                return None, None, None

            return result[0], result[1], message_content

        except (ValueError, AttributeError) as e:
            log.error(
                f"ModifierMenu | status=failed reason='Logic error in detail handler' user_id={user_id} error='{e}'",
                exc_info=True,
            )
            await Err.generic_error(call=call)
            return None, None, None

    results = await asyncio.gather(
        anim_service.animate_loading(duration=0.5, text="🔎 <b>Детализация...</b>"),
        run_logic(),
    )

    text, kb, message_content = results[1]
    if text is None:
        return

    chat_id, message_id = message_content
    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="html", reply_markup=kb)
    log.debug(f"UIRender | component=modifier_detail status=success user_id={user_id} modifier='{key}'")
