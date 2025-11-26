# app/handlers/callback/ui/status_menu/character_modifier.py
import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from app.resources.keyboards.status_callback import StatusModifierCallback
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from app.services.ui_service.status_menu.status_modifier_service import CharacterModifierUIService

router = Router(name="character_modifier_menu")


@router.callback_query(StatusModifierCallback.filter(F.level == "group"), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_modifier_group_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusModifierCallback, session: AsyncSession
) -> None:
    """
    Показывает список модификаторов в группе (Lvl 1).
    Теперь использует единый Агрегатор данных.
    """
    if not call.from_user:
        return

    await call.answer()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key

    log.info(f"User {user_id} открывает группу модификаторов: '{key}'")

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    async def run_logic():
        try:
            modifier_service = CharacterModifierUIService(char_id=char_id, key=key, state_data=state_data)

            # 🔥 ГЛАВНОЕ ИЗМЕНЕНИЕ:
            # Вместо if key == 'base_stats' ... else ..., мы всегда берем всё сразу.
            # Агрегатор вернет Wrapper, в котором есть И статы, И модификаторы.
            dto_to_use = await modifier_service.get_aggregated_data(session)

            if not dto_to_use:
                log.warning(f"Не удалось получить агрегированные данные для char_id={char_id}")
                await Err.generic_error(call)
                return None, None, None

            # Сервис сам разберется, какие поля достать из dto_to_use,
            # опираясь на настройки группы (key) в MODIFIER_HIERARCHY.
            result = modifier_service.status_group_modifier_message(dto_to_use)

            if not result or not result[0] or not result[1]:
                await Err.generic_error(call)
                return None, None, None

            message_content = modifier_service.get_message_content_data()
            if not message_content:
                await Err.message_content_not_found_in_fsm(call=call)
                return None, None, None

            return result[0], result[1], message_content

        except (ValueError, AttributeError, TypeError):
            await Err.generic_error(call)
            return None, None, None

    # Запускаем анимацию загрузки, так как расчет статов может занять время
    results = await asyncio.gather(
        anim_service.animate_loading(duration=1.0, text="📊 <b>Анализ показателей...</b>"),
        run_logic(),
    )

    text, kb, message_content = results[1]
    if text is None:
        return

    chat_id, message_id = message_content
    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="html", reply_markup=kb)
    # Сохраняем group_key, чтобы потом кнопка "Назад" из деталей знала, куда вернуться
    await state.update_data(group_key=key)


@router.callback_query(StatusModifierCallback.filter(F.level == "detail"), StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_modifier_detail_handler(
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusModifierCallback, session: AsyncSession
) -> None:
    """
    Показывает детали конкретного стата (Lvl 2).
    Также использует Агрегатор.
    """
    if not call.from_user:
        return

    await call.answer()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    key = callback_data.key

    log.info(f"User {user_id} смотрит детали модификатора: '{key}'")

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    async def run_logic():
        try:
            group_key = state_data.get("group_key")
            if not group_key:
                await Err.callback_data_missing(call=call)
                return None, None, None

            modifier_service = CharacterModifierUIService(char_id=char_id, key=key, state_data=state_data)

            # 🔥 Снова используем единый агрегатор
            dto_to_use = await modifier_service.get_aggregated_data(session)

            if not dto_to_use:
                await Err.generic_error(call=call)
                return None, None, None

            result = modifier_service.status_detail_modifier_message(dto_to_use=dto_to_use, group_key=group_key)

            if not result or not result[0] or not result[1]:
                await Err.generic_error(call)
                return None, None, None

            message_content = modifier_service.get_message_content_data()
            if not message_content:
                await Err.message_content_not_found_in_fsm(call=call)
                return None, None, None

            return result[0], result[1], message_content

        except (ValueError, AttributeError) as e:
            log.exception(f"Ошибка в деталях модификатора: {e}")
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
