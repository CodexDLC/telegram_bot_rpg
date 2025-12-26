from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bot.resources.fsm_states.states import InGame
from apps.bot.resources.keyboards.inventory_callback import InventoryCallback
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.bot.ui_service.helpers_ui.dto_helper import FSM_CONTEXT_KEY
from apps.common.core.container import AppContainer

router = Router(name="inventory_main_router")


@router.callback_query(
    InGame.inventory,
    InventoryCallback.filter(),  # Ловим ВСЕ уровни и действия
)
async def inventory_unified_handler(
    call: CallbackQuery,
    callback_data: InventoryCallback,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    container: AppContainer,
) -> None:
    """
    Единый хендлер для всей системы инвентаря.
    Делегирует обработку в InventoryBotOrchestrator.handle_callback.
    """
    user_id = call.from_user.id

    if user_id != callback_data.user_id:
        log.warning(f"Inventory | status=access_denied user_id={user_id} callback_user_id={callback_data.user_id}")
        await Err.access_denied(call)
        return

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")

    if not char_id:
        log.error(f"Inventory | status=failed reason='char_id not found in FSM' user_id={user_id}")
        await Err.char_id_not_found_in_fsm(call)
        return

    # Создаем оркестратор через контейнер
    orchestrator = container.get_inventory_bot_orchestrator(session)

    # --- ЕДИНАЯ ТОЧКА ВХОДА ---
    # Оркестратор сам решит, что делать (навигация или действие) и что вернуть (ViewDTO)
    result_dto = await orchestrator.handle_callback(char_id, user_id, callback_data, state_data)

    # Обновляем сообщение
    if result_dto.content and (coords := orchestrator.get_content_coords(state_data, user_id)):
        # Если есть item_id (например, при просмотре деталей), можно использовать его для логов или аналитики

        try:
            await bot.edit_message_text(
                chat_id=coords.chat_id,
                message_id=coords.message_id,
                text=result_dto.content.text,
                reply_markup=result_dto.content.kb,
                parse_mode="HTML",
            )
            log.info(
                f"Inventory | event=view_updated level={callback_data.level} action={callback_data.action} user_id={user_id}"
            )
        except TelegramAPIError as e:
            if "message is not modified" in str(e):
                # Игнорируем ошибку, если контент не изменился (например, нажали ту же страницу)
                await call.answer()
            else:
                log.error(f"Inventory | status=render_error error='{e}'")
                await Err.generic_error(call)
        except Exception as e:  # noqa: BLE001
            log.error(f"Inventory | status=render_error error='{e}'")
            await Err.generic_error(call)
    else:
        # Если content=None, значит действие выполнено, но UI обновлять не нужно (или это алерт)
        # В текущей реализации handle_callback всегда возвращает контент, но на будущее
        await call.answer()
