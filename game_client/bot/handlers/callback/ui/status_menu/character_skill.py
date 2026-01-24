from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from game_client.bot.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from game_client.bot.resources.keyboards.status_callback import SkillModeCallback, StatusSkillsCallback

# from apps.common.core.container import AppContainer

router = Router(name="character_skill_menu")


@router.callback_query(StatusSkillsCallback.filter(F.level == "group"), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_group_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    callback_data: StatusSkillsCallback,
    session: AsyncSession,
    container: Any,  # AppContainer
) -> None:
    """Обрабатывает нажатие на группу навыков и отображает список навыков в ней."""
    if not call.from_user or not call.message:
        return

    await call.answer()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key
    log.info(f"SkillMenu | event=group_selected user_id={user_id} char_id={char_id} group='{key}'")

    # state_data = await state.get_data()

    # orchestrator = container.get_status_bot_orchestrator(session)

    # result = await orchestrator.get_skill_view(char_id=char_id, level="group", key=key, state_data=state_data, bot=bot)

    # if result.content and (coords := orchestrator.get_content_coords(state_data)):
    #     await bot.edit_message_text(
    #         chat_id=coords.chat_id,
    #         message_id=coords.message_id,
    #         text=result.content.text,
    #         reply_markup=result.content.kb,
    #         parse_mode="HTML",
    #     )
    #     await state.update_data(group_key=key)
    #     log.debug(f"UIRender | component=skill_group status=success user_id={user_id} group='{key}'")
    # else:
    #     log.error(f"SkillMenu | status=failed reason='No content or coords' char_id={char_id}")
    #     await Err.generic_error(call=call)


@router.callback_query(StatusSkillsCallback.filter(F.level == "detail"), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_detail_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    callback_data: StatusSkillsCallback,
    session: AsyncSession,
    container: Any,  # AppContainer
) -> None:
    """Обрабатывает нажатие на конкретный навык и отображает его детальную информацию."""
    if not call.from_user:
        return

    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key
    log.info(f"SkillMenu | event=detail_selected user_id={user_id} char_id={char_id} skill='{key}'")

    # state_data = await state.get_data()

    # orchestrator = container.get_status_bot_orchestrator(session)

    # result = await orchestrator.get_skill_view(char_id=char_id, level="detail", key=key, state_data=state_data, bot=bot)

    # if result.content and (coords := orchestrator.get_content_coords(state_data)):
    #     await bot.edit_message_text(
    #         chat_id=coords.chat_id,
    #         message_id=coords.message_id,
    #         text=result.content.text,
    #         reply_markup=result.content.kb,
    #         parse_mode="HTML",
    #     )
    #     log.debug(f"UIRender | component=skill_detail status=success user_id={user_id} skill='{key}'")
    # else:
    #     log.error(f"SkillMenu | status=failed reason='No content or coords' char_id={char_id}")
    #     await Err.generic_error(call=call)


@router.callback_query(SkillModeCallback.filter(), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_skill_mode_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    callback_data: SkillModeCallback,
    session: AsyncSession,
    container: Any,  # AppContainer
) -> None:
    """Обрабатывает изменение режима прокачки навыка."""
    if not call.from_user or not call.message:
        return

    user_id = call.from_user.id
    log.info(
        f"SkillMenu | event=mode_change user_id={user_id} skill='{callback_data.skill_key}' new_mode='{callback_data.new_mode}'"
    )

    # orchestrator = container.get_status_bot_orchestrator(session)

    # # Вызываем метод оркестратора для смены режима
    # await orchestrator.change_skill_mode(
    #     char_id=callback_data.char_id, skill_key=callback_data.skill_key, new_mode=callback_data.new_mode
    # )

    await call.answer(f"Режим изменен на: {callback_data.new_mode}")

    # state_data = await state.get_data()

    # result = await orchestrator.get_skill_view(
    #     char_id=callback_data.char_id, level="detail", key=callback_data.skill_key, state_data=state_data, bot=bot
    # )

    # if result.content:
    #     await bot.edit_message_text(
    #         chat_id=call.message.chat.id,
    #         message_id=call.message.message_id,
    #         text=result.content.text,
    #         reply_markup=result.content.kb,
    #         parse_mode="HTML",
    #     )
