# apps/bot/handlers/callback/ui/menu_dispatch.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
from apps.bot.ui_service.menu_service import MenuService
from apps.game_core.game_service.game_sync_service import GameSyncService

if TYPE_CHECKING:
    from apps.common.core.container import AppContainer

router = Router(name="ui_menu_dispatch")


@router.callback_query(MeinMenuCallback.filter())
async def main_menu_dispatcher(
    call: CallbackQuery,
    callback_data: MeinMenuCallback,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    account_manager: Any,  # AccountManager
    container: AppContainer,
) -> None:
    if not call.from_user:
        return
    if callback_data.action != "refresh_menu":
        await call.answer()
    user_id = call.from_user.id
    char_id = callback_data.char_id
    action = callback_data.action
    log.info(f"MenuDispatch | event=action user_id={user_id} char_id={char_id} action='{action}'")

    sync_service = GameSyncService(session, account_manager)
    await sync_service.synchronize_player_state(char_id)

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    if session_context.get("char_id") != char_id:
        await Err.generic_error(call)
        return

    # --- REFRESH MENU (Нижнее сообщение) ---
    if action == "refresh_menu":
        menu_msg = session_context.get("message_menu")
        if not menu_msg:
            await Err.message_content_not_found_in_fsm(call)
            return
        await call.answer("🔄 Обновление данных...")
        # XXX: Очистить диспетчер от прямых импортов UI-сервисов.
        menu_service = MenuService(
            game_stage="in_game", state_data=state_data, session=session, account_manager=account_manager
        )
        final_text, final_kb = await menu_service.run_full_refresh_action()
        try:
            await bot.edit_message_text(
                chat_id=menu_msg["chat_id"],
                message_id=menu_msg["message_id"],
                text=final_text,
                reply_markup=final_kb,
                parse_mode="HTML",
            )
        except TelegramAPIError as e:
            log.warning(f"RefreshMenu | status=edit_failed error='{e}'")
        return

    # --- CONTENT SWITCHING (Верхнее сообщение) ---

    # Чтобы Mypy не ругался на смену типов, объявляем переменную явно
    result_dto: Any = None
    active_orchestrator: Any = None

    try:
        if action == "inventory":
            await state.set_state(InGame.inventory)
            inv_orc = container.get_inventory_bot_orchestrator(session)
            result_dto = await inv_orc.get_main_menu(char_id, user_id, state_data)
            active_orchestrator = inv_orc

        elif action == "navigation":
            await state.set_state(InGame.navigation)
            expl_orc = container.get_exploration_bot_orchestrator(session)
            result_dto = await expl_orc.get_current_view(char_id, state_data)
            active_orchestrator = expl_orc

        elif action == "status":
            # Статус не меняет стейт FSM (обычно), или меняет на InGame.status?
            # В character_status.py стейт не меняется явно, но лучше задать контекст.
            # Пока оставим текущий стейт или зададим InGame.status (если он есть).
            # В states.py есть FSM_CONTEX_CHARACTER_STATUS = [InGame.navigation, InGame.inventory, InGame.combat]
            # Значит, статус доступен из любого стейта.
            # Но лучше переключить на InGame.navigation (как дефолт) или оставить как есть.

            stat_orc = container.get_status_bot_orchestrator(session)
            result_dto = await stat_orc.get_status_view(char_id, "bio", state_data, bot)
            active_orchestrator = stat_orc

        else:
            await call.answer("Раздел недоступен.", show_alert=True)
            return

        # Теперь общая логика отрисовки
        if result_dto and result_dto.content and active_orchestrator:
            # Для InventoryBotOrchestrator get_content_coords требует user_id, для других - нет (или опционально)
            # Проверяем сигнатуру или передаем user_id, если метод его принимает.
            # В IBotOrchestrator user_id опционален.
            # Но InventoryBotOrchestrator.get_content_coords требует user_id.
            # ExplorationBotOrchestrator.get_content_coords(state_data)
            # StatusBotOrchestrator.get_content_coords(state_data, user_id=None)

            # Попытаемся передать user_id, если это инвентарь, иначе без него (или с None)
            # Но проще передать user_id всегда, если сигнатура позволяет.
            # В InventoryBotOrchestrator: def get_content_coords(self, state_data: dict, user_id: int) -> MessageCoordsDTO | None:
            # В ExplorationBotOrchestrator: def get_content_coords(self, state_data: dict) -> MessageCoordsDTO | None:
            # В StatusBotOrchestrator: def get_content_coords(self, state_data: dict, user_id: int | None = None) -> MessageCoordsDTO | None:

            # Приводим к общему виду или делаем проверку
            coords = None
            if hasattr(active_orchestrator, "get_content_coords"):
                # Проверка на инвентарь костылем, пока не приведем к единому интерфейсу
                # Но лучше использовать try/except TypeError или inspect, но это медленно.
                # В InventoryBotOrchestrator user_id обязателен.
                try:
                    coords = active_orchestrator.get_content_coords(state_data, user_id=user_id)
                except TypeError:
                    coords = active_orchestrator.get_content_coords(state_data)

            if coords:
                await bot.edit_message_text(
                    chat_id=coords.chat_id,
                    message_id=coords.message_id,
                    text=result_dto.content.text,
                    reply_markup=result_dto.content.kb,
                    parse_mode="HTML",
                )

    except (TelegramAPIError, ValueError) as e:
        log.exception(f"MenuDispatch | status=failed action='{action}' error='{e}'")
        await Err.generic_error(call)
