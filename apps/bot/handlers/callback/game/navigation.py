# apps/bot/handlers/callback/game/navigation.py
import asyncio
import contextlib

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.callback_data import NavigationCallback
from apps.bot.ui_service.exploration.exploration_ui import ExplorationUIService
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from apps.bot.ui_service.hub_entry_service import HubEntryService
from apps.common.schemas_dto import SessionDataDTO
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.arena_manager import ArenaManager
from apps.common.services.core_service.manager.combat_manager import CombatManager

router = Router(name="game_navigation_router")

TRAVEL_FLAVOR_TEXTS = [
    "Вы внимательно смотрите под ноги...",
    "Ветер шумит в ушах...",
    "Вдали слышны странные звуки...",
    "Дорога кажется бесконечной...",
    "Вы поправляете снаряжение на ходу...",
]


@router.callback_query(InGame.navigation, NavigationCallback.filter(F.action == "move"))
async def navigation_move_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    callback_data: NavigationCallback,
    exploration_ui_service: ExplorationUIService,
) -> None:
    """Обрабатывает перемещение с немедленной анимацией."""
    if not call.from_user:
        return

    user_id = call.from_user.id
    target_loc_id = callback_data.target_id
    travel_time = callback_data.t

    log.info(f"Navigation | event=move_start user_id={user_id} target='{target_loc_id}' travel_time={travel_time}s")

    with contextlib.suppress(TelegramAPIError):
        await call.answer()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    message_content = session_context.get("message_content")
    actor_name = session_context.get("symbiote_name", "Симбиот")

    if not char_id or not message_content:
        log.error(f"Navigation | status=failed reason='char_id or message_content missing' user_id={user_id}")
        await Err.generic_error(call)
        return

    async def animate_task():
        if travel_time >= 2.0:
            log.debug(f"Navigation | animation=start duration={travel_time}s char_id={char_id}")
            session_dto = SessionDataDTO(**session_context)
            anim_service = UIAnimationService(bot=bot, message_data=session_dto)
            await anim_service.animate_navigation(duration=travel_time, flavor_texts=TRAVEL_FLAVOR_TEXTS)
        else:
            await asyncio.sleep(travel_time or 0.3)

    async def backend_task():
        return await exploration_ui_service.move_character(
            char_id=char_id, target_loc_id=target_loc_id, actor_name=actor_name
        )

    # Запускаем обе задачи одновременно
    _, (text, kb) = await asyncio.gather(animate_task(), backend_task())

    try:
        await bot.edit_message_text(
            chat_id=message_content["chat_id"],
            message_id=message_content["message_id"],
            text=text,
            reply_markup=kb,
            parse_mode="HTML",
        )
        log.info(f"Navigation | event=move_end status=success user_id={user_id} target_loc='{target_loc_id}'")
    except TelegramAPIError as e:
        log.error(f"UIRender | component=navigation status=failed user_id={user_id} error='{e}'")


@router.callback_query(InGame.navigation, F.data.startswith("svc:"))
async def navigation_service_handler(
    call: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    account_manager: AccountManager,
    arena_manager: ArenaManager,
    combat_manager: CombatManager,
):
    if not call.data or not call.from_user:
        await call.answer()
        return

    service_id = call.data.split(":")[-1]
    user_id = call.from_user.id
    log.info(f"Navigation | event=service_enter user_id={user_id} service_id='{service_id}'")
    await call.answer()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    message_content = session_context.get("message_content")

    if not char_id or not message_content:
        log.error(f"Navigation | status=failed reason='char_id or message_content missing' user_id={user_id}")
        await Err.generic_error(call)
        return

    hub_entry_service = HubEntryService(
        char_id=char_id,
        target_loc=service_id,
        state_data=state_data,
        session=session,
        account_manager=account_manager,
        arena_manager=arena_manager,
        combat_manager=combat_manager,
    )

    text, kb, new_fsm_state = await hub_entry_service.render_hub_menu()

    if not text:
        await call.answer("Сервис временно недоступен.", show_alert=True)
        return

    await state.set_state(new_fsm_state)
    log.debug(f"FSM | user_id={user_id} state={new_fsm_state}")

    await bot.edit_message_text(
        chat_id=message_content["chat_id"],
        message_id=message_content["message_id"],
        text=text,
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(InGame.navigation, F.data.startswith("nav:action:"))
async def navigation_action_stub(call: CallbackQuery):
    if not call.data:
        await call.answer()
        return
    action = call.data.split(":")[-1]

    responses = {
        "search": "🔍 Вы начинаете прочесывать сектор... (Механика в разработке)",
        "battles": "⚔️ Сканирование эфира... (Механика в разработке)",
        "safe_zone": "🕊 Здесь действует Пакт о ненападении.",
        "people": "👥 Загрузка списка сталкеров... (Механика в разработке)",
        "auto": "🧭 Системы авто-навигации калибруются... (Механика в разработке)",
        "look_around": "👁 Данные обновлены.",
        "ignore": None,
    }

    text = responses.get(action, "Функция недоступна.")

    if action == "ignore":
        await call.answer()
        return

    if action == "look_around":
        await call.answer("Сканирование завершено.")
        return

    await call.answer(text, show_alert=True)
