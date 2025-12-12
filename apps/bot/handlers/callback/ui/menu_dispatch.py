# TODO [ARCH-DEBT]: Legacy Handler. Требует рефакторинга для работы через API Gateway (убрать прямые импорты game_core).
from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.callback_data import MeinMenuCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.bot.ui_service.inventory.inventory_ui_service import InventoryUIService
from apps.bot.ui_service.menu_service import MenuService
from apps.bot.ui_service.navigation_service import NavigationService
from apps.common.services.core_service.manager.account_manager import AccountManager
from apps.common.services.core_service.manager.combat_manager import CombatManager
from apps.common.services.core_service.manager.world_manager import WorldManager
from apps.game_core.game_service.game_sync_service import GameSyncService
from apps.game_core.game_service.world.game_world_service import GameWorldService

router = Router(name="ui_menu_dispatch")


@router.callback_query(MeinMenuCallback.filter())
async def main_menu_dispatcher(
    call: CallbackQuery,
    callback_data: MeinMenuCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    account_manager: AccountManager,
    world_manager: WorldManager,
    game_world_service: GameWorldService,
    combat_manager: CombatManager,
) -> None:
    """
    Единая точка входа из Главного Меню.
    Переключает режимы (FSM) и вызывает соответствующие сервисы UI.
    """
    if not call.from_user:
        return

    # Не отвечаем сразу на call.answer() для quick_heal, чтобы не сбивать анимацию "часиков",
    # или отвечаем, но потом редактируем сообщение.
    # Для остальных - отвечаем сразу.
    if callback_data.action != "quick_heal":
        await call.answer()

    user_id = call.from_user.id
    char_id = callback_data.char_id
    action = callback_data.action

    log.info(f"MenuDispatch | event=action user_id={user_id} char_id={char_id} action='{action}'")

    # 1. Синхронизация состояния (Реген)
    sync_service = GameSyncService(session, account_manager)
    await sync_service.synchronize_player_state(char_id)

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})

    if session_context.get("char_id") != char_id:
        log.warning(f"MenuDispatch | reason='char_id mismatch' user_id={user_id}")
        await Err.generic_error(call)
        return

    # ==========================================
    # 🔄 ОБНОВЛЕНИЕ МЕНЮ (Бывшее quick_heal)
    # ==========================================

    if action == "refresh_menu":  # <--- ИЗМЕНЕНО: Новое имя действия
        menu_msg = session_context.get("message_menu")
        if not menu_msg:
            await Err.message_content_not_found_in_fsm(call)
            return

        await call.answer("🔄 Обновление данных...")

        # 1. Выполняем "мгновенную" логику
        menu_service = MenuService(
            game_stage="in_game", state_data=state_data, session=session, account_manager=account_manager
        )

        # Получаем результат сразу (Time Delta + актуальные данные)
        final_text, final_kb = await menu_service.run_full_refresh_action()  # <--- Используем существующий метод

        # 2. Обновляем сообщение меню
        try:
            await bot.edit_message_text(
                chat_id=menu_msg["chat_id"],
                message_id=menu_msg["message_id"],
                text=final_text,
                reply_markup=final_kb,
                parse_mode="HTML",
            )
        except TelegramAPIError as e:
            # Логгируем, если сообщение не удалось обновить (например, слишком старое или удалено)
            log.warning(f"RefreshMenu | status=edit_failed error='{e}'")

        return

    # --- ОСТАЛЬНЫЕ КНОПКИ (Инвентарь, Навигация) ---
    # Для них нужно сообщение КОНТЕНТА (нижнее)
    content_msg = session_context.get("message_content")
    if not content_msg:
        log.error(f"MenuDispatch | status=failed reason='message_content not found' user_id={user_id}")
        await Err.generic_error(call)
        return

    chat_id = content_msg["chat_id"]
    message_id = content_msg["message_id"]

    try:
        text, kb = None, None

        if action == "inventory":
            await state.set_state(InGame.inventory)
            service = InventoryUIService(
                char_id=char_id,
                session=session,
                user_id=user_id,
                state_data=state_data,
                account_manager=account_manager,
            )
            text, kb = await service.render_main_menu()

        elif action == "navigation":
            await state.set_state(InGame.navigation)
            nav_service = NavigationService(
                char_id=char_id,
                state_data=state_data,
                account_manager=account_manager,
                world_manager=world_manager,
                game_world_service=game_world_service,
                combat_manager=combat_manager,
            )
            text, kb = await nav_service.reload_current_ui()

        # --- (Тут можно добавить еще условия) ---

        if text and kb:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
            )
        else:
            await call.answer("Раздел недоступен.", show_alert=True)

    except (TelegramAPIError, ValueError) as e:  # Заменено на более конкретные исключения
        log.exception(f"MenuDispatch | status=failed action='{action}' error='{e}'")
        await Err.generic_error(call)
