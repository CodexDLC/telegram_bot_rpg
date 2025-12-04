from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import ArenaState
from app.resources.keyboards.callback_data import ArenaQueueCallback
from app.services.helpers_module.universal_stub import UniversalStubService

router = Router(name="arena_tournament_router")

# Создаем экземпляр сервиса-заглушки
stub_service = UniversalStubService("👥 Хаотические бои находятся в разработке.")


@router.callback_query(ArenaState.menu, ArenaQueueCallback.filter(F.action == "match_menu_chaotic"))
async def tournament_handler_placeholder(call: CallbackQuery, callback_data: ArenaQueueCallback):
    """Заглушка для обработки хаотических боев."""
    await stub_service.handle_callback(call, callback_data)
