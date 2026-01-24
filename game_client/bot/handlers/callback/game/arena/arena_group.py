from aiogram import F, Router
from aiogram.types import CallbackQuery

from game_client.bot.resources.fsm_states.states import ArenaState
from game_client.bot.resources.keyboards.callback_data import ArenaQueueCallback
from game_client.bot.ui_service.helpers_ui.universal_stub import UniversalStubService

router = Router(name="arena_group_router")

# Создаем экземпляр сервиса-заглушки
stub_service = UniversalStubService("🛡️ Групповые бои находятся в разработке.")


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "match_menu_fixed"))
async def group_handler_placeholder(call: CallbackQuery, callback_data: ArenaQueueCallback):
    """Заглушка для обработки групповых боев."""
    await stub_service.handle_callback(call, callback_data)
