import asyncio
import contextlib
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.callback_data import NavigationCallback
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.services.core_service.manager.account_manager import AccountManager
from app.services.core_service.manager.combat_manager import CombatManager
from app.services.core_service.manager.world_manager import WorldManager
from app.services.game_service.world.game_world_service import GameWorldService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay
from app.services.ui_service.navigation_service import NavigationService

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
    account_manager: AccountManager,
    world_manager: WorldManager,
    game_world_service: GameWorldService,
    combat_manager: CombatManager,
) -> None:
    """Обрабатывает перемещение игрока между локациями."""
    if not call.from_user:
        return

    start_time = time.monotonic()
    user_id = call.from_user.id
    target_loc_id = callback_data.target_id

    log.info(f"Navigation | event=move_start user_id={user_id} target_loc='{target_loc_id}'")

    with contextlib.suppress(TelegramAPIError):
        await call.answer()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    message_content = session_context.get("message_content")

    if not char_id or not message_content:
        log.error(f"Navigation | status=failed reason='char_id or message_content missing' user_id={user_id}")
        await Err.generic_error(call)
        return

    nav_service = NavigationService(
        char_id=char_id,
        state_data=state_data,
        account_manager=account_manager,
        world_manager=world_manager,
        game_world_service=game_world_service,
        symbiote_name=None,
        combat_manager=combat_manager,
    )
    result = await nav_service.move_player(target_loc_id)
    log.debug(f"Navigation | move_player_result='{result}' char_id={char_id}")

    if not result:
        log.warning(f"Navigation | status=failed reason='move_player returned None' char_id={char_id}")
        with contextlib.suppress(TelegramAPIError):
            await call.answer("Действие недоступно.", show_alert=True)
        return

    total_travel_time, text, kb = result
    chat_id = message_content["chat_id"]
    message_id = message_content["message_id"]

    if kb is None:
        log.warning(f"Navigation | status=failed reason='Navigation logic error' user_id={user_id}")
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML")
        except TelegramBadRequest as e:
            log.warning(f"UIRender | component=nav_error status=not_modified user_id={user_id} error='{e}'")
        except TelegramAPIError as e:
            log.error(f"UIRender | component=nav_error status=failed user_id={user_id} error='{e}'")

        await asyncio.sleep(2)

        log.debug(f"Navigation | action=reload_ui char_id={char_id}")
        restore_text, restore_kb = await nav_service.reload_current_ui()
        if restore_text and restore_kb:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=restore_text,
                    reply_markup=restore_kb,
                    parse_mode="HTML",
                )
            except TelegramAPIError as e:
                log.error(f"UIRender | component=nav_restore status=failed user_id={user_id} error='{e}'")
        return

    if total_travel_time >= 2.0:
        log.debug(f"Navigation | animation=start duration={total_travel_time}s char_id={char_id}")
        session_dto = SessionDataDTO(**session_context)
        anim_service = UIAnimationService(bot=bot, message_data=session_dto)
        await anim_service.animate_navigation(duration=total_travel_time, flavor_texts=TRAVEL_FLAVOR_TEXTS)
    else:
        await await_min_delay(start_time, min_delay=total_travel_time or 0.3)

    try:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
        )
        log.info(f"Navigation | event=move_end status=success user_id={user_id} target_loc='{target_loc_id}'")
    except TelegramAPIError as e:
        log.error(f"UIRender | component=navigation status=failed user_id={user_id} error='{e}'")


@router.callback_query(InGame.navigation, F.data.startswith("nav:action:"))
async def navigation_action_stub(call: CallbackQuery):
    """
    Обработчик функциональных кнопок навигационной панели.
    """
    if not call.data:
        await call.answer()
        return
    action = call.data.split(":")[-1]

    responses = {
        "search": "🔍 Вы начинаете прочесывать сектор в поисках ресурсов и врагов... (Механика в разработке)",
        "battles": "⚔️ Сканирование эфира на наличие активных боевых сигнатур... (Механика в разработке)",
        "safe_zone": "🕊 Здесь действует Пакт о ненападении. Бои между игроками запрещены.",
        "people": "👥 Загрузка списка сталкеров в радиусе видимости... (Механика в разработке)",
        "auto": "🧭 Системы авто-навигации калибруются. Выберите точку назначения... (Механика в разработке)",
        "look_around": "👁 Данные обновлены.",
        "ignore": None,
    }

    text = responses.get(action, "Функция недоступна.")

    if action == "ignore":
        await call.answer()
        return

    # Для осмотра можно делать реальный рефреш UI
    if action == "look_around":
        # Тут в будущем будет вызов метода обновления
        await call.answer("Сканирование завершено.")
        return

    await call.answer(text, show_alert=True)
