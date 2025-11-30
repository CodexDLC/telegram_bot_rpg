# app/handlers/callback/game/hub_entry.py
import asyncio

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

# --- Импорт FSM-состояния ---
from app.resources.fsm_states.states import InGame

# --- Импорт CallbackData ---
from app.resources.keyboards.callback_data import ServiceEntryCallback

# --- Импорт DTO и Хелперов ---
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
from app.services.game_service.hub_entry_service import HubEntryService
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
from app.services.helpers_module.dto_helper import FSM_CONTEXT_KEY
from app.services.ui_service.base_service import BaseUIService
from app.services.ui_service.helpers_ui.ui_animation_service import UIAnimationService

router = Router(name="hub_entry_router")


@router.callback_query(InGame.navigation, ServiceEntryCallback.filter())
async def service_hub_entry_handler(
    call: CallbackQuery, callback_data: ServiceEntryCallback, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    """
    Обрабатывает вход в любой Сервисный Хаб (Арена, Таверна, Рифт и т.д.).

    Args:
        call (CallbackQuery): Callback от кнопки сервисного входа.
        callback_data (ServiceEntryCallback): Распарсенные данные колбэка.
        state (FSMContext): Контекст FSM.
        bot (Bot): Экземпляр бота.
        session (AsyncSession): Сессия базы данных.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'service_hub_entry_handler' получил обновление без 'from_user'.")
        return

    target_loc = callback_data.target_loc
    char_id = callback_data.char_id

    log.info(f"Хэндлер 'service_hub_entry_handler' вызван. Вход в хаб: '{target_loc}'.")
    await call.answer()

    # 0. Проверка ID
    if not char_id:
        await Err.char_id_not_found_in_fsm(call)
        return

    # --- 1. Анимация ---
    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    session_dto = SessionDataDTO(**session_context)
    anim_service = UIAnimationService(bot=bot, message_data=session_dto)

    async def run_logic():
        # Создаем ваш сервис, который будет содержать логику рендеринга и FSM-перехода
        hub_service = HubEntryService(char_id=char_id, target_loc=target_loc, state_data=state_data, session=session)

        # Вызываем главный метод рендеринга
        text, kb, new_fsm_state = await hub_service.render_hub_menu()

        # Обновляем FSM-состояние
        await state.set_state(new_fsm_state)
        log.info(f"FSM state установлен в '{new_fsm_state}'.")

        return text, kb

    # Запуск анимации (параллельно с логикой)
    results = await asyncio.gather(
        anim_service.animate_loading(duration=1.0, text="🚪 <b>Открытие доступа...</b>"),
        run_logic(),
    )

    text, kb = results[1]

    if text is None:
        await Err.generic_error(call)
        return

    # --- 2. Редактирование сообщения ---
    base_ui_service = BaseUIService(state_data=state_data)
    message_data = base_ui_service.get_message_content_data()

    if not message_data:
        await Err.message_content_not_found_in_fsm(call)
        return

    chat_id, message_id = message_data

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="html",
            reply_markup=kb,
        )
        log.info(f"UI для хаба '{target_loc}' успешно обновлено.")

    except TelegramAPIError as e:
        log.error(f"Ошибка редактирования сообщения в service_hub_entry_handler: {e}", exc_info=True)
        await Err.generic_error(call)
