import time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage
from loguru import logger as log

from apps.bot.resources.fsm_states import InGame
from apps.bot.resources.keyboards.combat_callback import CombatActionCallback
from apps.bot.ui_service.combat.combat_bot_orchestrator import CombatBotOrchestrator
from apps.bot.ui_service.helpers_ui.callback_exceptions import UIErrorHandler as Err
from apps.common.schemas_dto.combat_source_dto import CombatMoveDTO

action_router = Router(name="combat_actions")


@action_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "submit"))
async def submit_turn_handler(
    call: CallbackQuery, callback_data: CombatActionCallback, state: FSMContext, orchestrator: CombatBotOrchestrator
):
    """
    Хэндлер подтверждения хода (Submit).
    Собирает данные из FSM и отправляет их в оркестратор.
    """
    if not call.message or isinstance(call.message, InaccessibleMessage):
        return await call.answer("Сообщение недоступно.")

    state_data = await state.get_data()

    # 1. Извлекаем необходимые данные из FSM
    char_id = state_data.get("char_id")
    session_id = state_data.get("combat_session_id")
    target_id = state_data.get("combat_target_id")
    selection = state_data.get("combat_selection", {})

    if not char_id or not session_id or not target_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    # 2. Формируем DTO хода (пулю)
    execute_at = int(time.time()) + 60

    move_dto = CombatMoveDTO(
        target_id=int(target_id),
        attack_zones=selection.get("atk", []),
        block_zones=selection.get("def", []),
        ability_key=state_data.get("combat_selected_ability"),
        execute_at=execute_at,
    )

    try:
        # 3. Оркестратор сам сделает запрос в Ядро и решит, какой UI вернуть
        text, kb = await orchestrator.handle_submit(session_id, char_id, move_dto)

        # 4. Обновляем сообщение и очищаем выбор зон в FSM для следующей цели
        await state.update_data(combat_selection={}, combat_selected_ability=None)
        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        await call.answer("Ход подтвержден!")

    except Exception as e:  # noqa: BLE001
        log.exception(f"ActionHandler | status=failed char_id={char_id} error={e}")
        await Err.report_and_restart(call, "Не удалось отправить ход в Ядро.")


@action_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "refresh"))
async def refresh_combat_handler(call: CallbackQuery, state: FSMContext, orchestrator: CombatBotOrchestrator):
    """
    Хэндлер ручного обновления экрана боя.
    """
    if not call.message or isinstance(call.message, InaccessibleMessage):
        return await call.answer("Сообщение недоступно.")

    state_data = await state.get_data()
    char_id = state_data.get("char_id")
    session_id = state_data.get("combat_session_id")
    selection = state_data.get("combat_selection", {})

    if not char_id or not session_id:
        return await Err.report_and_restart(call, "Данные сессии боя утеряны.")

    try:
        # Просто запрашиваем актуальный вид у оркестратора
        text, kb = await orchestrator.get_dashboard_view(session_id, char_id, selection)

        await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        await call.answer("Экран обновлен")

    except Exception as e:  # noqa: BLE001
        log.error(f"ActionHandler | refresh failed: {e}")
        await Err.report_and_restart(call, "Сбой при получении данных боя.")


@action_router.callback_query(InGame.combat, CombatActionCallback.filter(F.action == "leave"))
async def leave_combat_handler(call: CallbackQuery, state: FSMContext):
    """
    Завершает участие в бою и переводит игрока в навигацию.
    """
    if not call.message or isinstance(call.message, InaccessibleMessage):
        return await call.answer("Сообщение недоступно.")

    # Здесь можно добавить проверку через оркестратор, действительно ли бой окончен
    await state.set_state(InGame.navigation)
    await state.update_data(combat_session_id=None, combat_target_id=None)

    await call.message.edit_text("Вы покинули поле боя. Возвращение в мир...")
    await call.answer()
