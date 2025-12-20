import asyncio

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.callback_data import ServiceEntryCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.bot.ui_service.hub_entry_service import HubEntryService
from apps.common.core.container import AppContainer
from apps.common.schemas_dto import SessionDataDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.arena_manager import ArenaManager
from apps.common.services.core_service.manager.combat_manager import CombatManager

router = Router(name="hub_entry_router")


@router.callback_query(InGame.navigation, ServiceEntryCallback.filter())
async def service_hub_entry_handler(
    call: CallbackQuery,
    callback_data: ServiceEntryCallback,
    state: FSMContext,
    bot: Bot,
    container: AppContainer,
    session: AsyncSession,
    account_manager: AccountManager,
    arena_manager: ArenaManager,
    combat_manager: CombatManager,
) -> None:
    """Обрабатывает вход в любой сервисный хаб (Арена, Таверна и т.д.)."""
    if not call.from_user:
        return

    target_loc = callback_data.target_loc
    char_id = callback_data.char_id
    user_id = call.from_user.id

    log.info(f"HubEntry | event=start user_id={user_id} char_id={char_id} target_loc='{target_loc}'")
    await call.answer()

    if not char_id:
        log.warning(f"HubEntry | status=failed reason='char_id not found in callback' user_id={user_id}")
        await Err.char_id_not_found_in_fsm(call)
        return

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    # Создаем оркестратор для получения координат (мы еще в навигации)
    orchestrator = container.get_exploration_bot_orchestrator(session)

    async def run_logic():
        hub_service = HubEntryService(
            char_id=char_id,
            target_loc=target_loc,
            state_data=state_data,
            session=session,
            account_manager=account_manager,
            arena_manager=arena_manager,
            combat_manager=combat_manager,
        )
        text, kb, new_fsm_state = await hub_service.render_hub_menu()
        await state.set_state(new_fsm_state)
        log.info(f"FSM | state={new_fsm_state} user_id={user_id} char_id={char_id}")
        return text, kb

    results = await asyncio.gather(
        anim_service.animate_loading(duration=1.0, text="🚪 <b>Открытие доступа...</b>"),
        run_logic(),
    )

    text, kb = results[1]
    if text is None:
        log.error(
            f"HubEntry | status=failed reason='render_hub_menu returned None' user_id={user_id} char_id={char_id}"
        )
        await Err.generic_error(call)
        return

    # Используем оркестратор для получения координат
    if coords := orchestrator.get_content_coords(state_data):
        try:
            await bot.edit_message_text(
                chat_id=coords.chat_id, message_id=coords.message_id, text=text, parse_mode="html", reply_markup=kb
            )
            log.debug(f"UIRender | component=hub_menu status=success user_id={user_id} hub='{target_loc}'")
        except TelegramAPIError:
            log.exception(f"UIRender | component=hub_menu status=failed user_id={user_id} hub='{target_loc}'")
            await Err.generic_error(call)
    else:
        log.error(f"HubEntry | status=failed reason='message_content not found in FSM' user_id={user_id}")
        await Err.message_content_not_found_in_fsm(call)
