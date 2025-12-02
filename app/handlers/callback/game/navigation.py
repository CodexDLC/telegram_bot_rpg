# app/handlers/callback/game/navigation.py
import asyncio
import contextlib
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.callback_data import NavigationCallback
from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO
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
    call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: NavigationCallback, session: AsyncSession
) -> None:
    """
    Обрабатывает перемещение игрока с таймером и обработкой ошибок.
    """
    if not call.from_user:
        return

    start_time = time.monotonic()
    user_id = call.from_user.id
    target_loc_id = callback_data.target_id

    log.info(f"User {user_id} инициировал переход в локацию '{target_loc_id}'.")

    # Отвечаем на callback сразу
    with contextlib.suppress(TelegramAPIError):
        await call.answer()

    state_data = await state.get_data()
    session_context = state_data.get(FSM_CONTEXT_KEY, {})
    char_id = session_context.get("char_id")
    message_content = session_context.get("message_content")
    log.debug(f"MoveHandler | char_id={char_id}, message_content exists: {bool(message_content)}")

    if not char_id or not message_content:
        log.error(f"В FSM user {user_id} отсутствуют данные char_id или message_content.")
        await Err.generic_error(call)
        return

    nav_service = NavigationService(char_id=char_id, state_data=state_data)
    log.debug("MoveHandler | NavigationService_initialized")

    # Выполняем перемещение
    result = await nav_service.move_player(target_loc_id)
    log.debug(f"MoveHandler | move_player_result: {result}")

    if not result:
        # Ошибка на уровне "вообще ничего не вернулось" (например, аккаунт не найден)
        log.warning(f"MoveHandler | move_player вернул None для char_id={char_id}")
        with contextlib.suppress(TelegramAPIError):
            await call.answer("Действие недоступно.", show_alert=True)
        return

    total_travel_time, text, kb = result
    chat_id = message_content["chat_id"]
    message_id = message_content["message_id"]
    log.debug(f"MoveHandler | travel_time={total_travel_time}, text_len={len(text)}, kb_exists={bool(kb)}")

    # --- ОБРАБОТКА ОШИБКИ ПЕРЕХОДА (Fail-safe) ---
    # Если клавиатуры нет (None), значит сервис сообщил об ошибке логики (локация удалена и т.д.)
    if kb is None:
        log.warning(f"User {user_id}: Ошибка навигации (локация не найдена). Откат.")

        # 1. Показываем текст ошибки (без кнопок)
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,  # Текст ошибки из сервиса
                parse_mode="HTML",
            )
        except TelegramBadRequest as e:
            log.warning(f"Не удалось показать ошибку (сообщение не изменилось): {e}")
        except TelegramAPIError as e:
            log.error(f"Не удалось показать ошибку: {e}")

        # 2. Ждем 2 секунды, чтобы игрок прочитал
        await asyncio.sleep(2)

        # 3. Восстанавливаем экран ТЕКУЩЕЙ (старой) локации
        # Игрок никуда не перешел, база данных не менялась.
        log.debug(f"MoveHandler | Вызов reload_current_ui для char_id={char_id}")
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
                log.error(f"Не удалось восстановить UI после ошибки: {e}")
        return
        # ---------------------------------------------

    # Если ошибок нет, запускаем таймер пути
    if total_travel_time > 2:
        log.debug(f"MoveHandler | Запуск анимации на {total_travel_time} сек.")
        # 1. Превращаем словарь session_context обратно в DTO
        # (UIAnimationService ожидает объект, а не словарь)
        session_dto = SessionDataDTO(**session_context)

        # 2. Инициализируем сервис анимации
        anim_service = UIAnimationService(bot=bot, message_data=session_dto)

        # 3. Запускаем анимацию навигации
        # (TRAVEL_FLAVOR_TEXTS берем из этого же файла, он определен выше)
        await anim_service.animate_navigation(duration=total_travel_time, flavor_texts=TRAVEL_FLAVOR_TEXTS)

    else:
        # Короткая задержка для быстрых переходов
        await await_min_delay(start_time, min_delay=total_travel_time or 0.3)

    # Финальное обновление UI (Показ новой локации)
    try:
        log.debug(f"MoveHandler | Финальное обновление UI на локацию {target_loc_id}")
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
        )
        log.info(f"User {user_id} успешно перешел в '{target_loc_id}'.")

    except TelegramAPIError as e:
        log.error(f"Ошибка при обновлении сообщения локации: {e}")
