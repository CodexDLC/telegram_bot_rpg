# app/handlers/callback/game/navigation.py
import asyncio
import contextlib
import random
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.fsm_states.states import InGame
from app.resources.keyboards.callback_data import NavigationCallback
from app.services.helpers_module.callback_exceptions import UIErrorHandler as Err
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
    char_id = state_data.get("char_id")
    message_content = state_data.get("message_content")

    if not char_id or not message_content:
        log.error(f"В FSM user {user_id} отсутствуют данные char_id или message_content.")
        await Err.generic_error(call)
        return

    nav_service = NavigationService(char_id=char_id, state_data=state_data)

    # Выполняем перемещение
    result = await nav_service.move_player(target_loc_id)

    if not result:
        # Ошибка на уровне "вообще ничего не вернулось" (например, аккаунт не найден)
        with contextlib.suppress(TelegramAPIError):
            await call.answer("Действие недоступно.", show_alert=True)
        return

    total_travel_time, text, kb = result
    chat_id = message_content["chat_id"]
    message_id = message_content["message_id"]

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
        remaining_time = int(total_travel_time)
        flavor_text = random.choice(TRAVEL_FLAVOR_TEXTS)

        try:
            while remaining_time > 0:
                # Рисуем прогресс-бар
                filled = int(total_travel_time) - remaining_time
                empty = remaining_time
                # Ограничиваем длину бара
                max_bar_len = 10
                if total_travel_time > max_bar_len:
                    scale = max_bar_len / total_travel_time
                    filled = int(filled * scale)
                    empty = max_bar_len - filled

                progress_bar = "■" * filled + "□" * empty

                wait_text = (
                    f"👣 <b>В пути...</b>\n"
                    f"<i>{flavor_text}</i>\n\n"
                    f"⏳ <code>[{progress_bar}] {remaining_time} сек.</code>"
                )

                with contextlib.suppress(TelegramBadRequest):
                    await bot.edit_message_text(
                        chat_id=chat_id, message_id=message_id, text=wait_text, reply_markup=None, parse_mode="HTML"
                    )

                step = 1.5
                await asyncio.sleep(step)
                remaining_time -= int(step) if step >= 1 else 1

        except asyncio.CancelledError:
            log.warning("Анимация перехода была отменена.")
        except Exception as e:  # noqa: BLE001
            log.warning(f"Ошибка в цикле анимации перехода: {e}")

    else:
        # Короткая задержка
        await await_min_delay(start_time, min_delay=total_travel_time or 0.3)

    # Финальное обновление UI (Показ новой локации)
    try:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=kb, parse_mode="HTML"
        )
        log.info(f"User {user_id} успешно перешел в '{target_loc_id}'.")

    except TelegramAPIError as e:
        log.error(f"Ошибка при обновлении сообщения локации: {e}")
