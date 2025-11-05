# app/handlers/callback/ui/status_menu/character_status.py
import logging
import time
from typing import Union

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from app.resources.keyboards.callback_data import StatusMenuCallback
from app.resources.texts.ui_messages import TEXT_AWAIT
from app.services.helpers_module.DTO_helper import fsm_convector
from app.services.helpers_module.get_data_handlers.status_data_helper import get_status_data_package
from app.services.helpers_module.helper_id_callback import error_int_id, error_msg_default
from app.services.ui_service.character_status_service import CharacterMenuUIService
from app.services.ui_service.helpers_ui.ui_tools import await_min_delay

router = Router(name="character_status_menu")

log = logging.getLogger(__name__)


async def status_menu_start_handler(state: FSMContext,
                                    bot: Bot,
                                    call: Union[CallbackQuery, None] = None,
                                    # VVV Параметры, которые передаст хэндлер VVV
                                    explicit_char_id: int = None,
                                    explicit_view_mode: str = None,
                                    explicit_call_type: str = None,
                                    ):
    """
    ОСНОВНАЯ ЛОГИКА: Выводит или обновляет статус персонажа.
    (Режим 1: call=CallbackQuery, Режим 2: call=None)
    """

    log.info("status_menu_start_handler (ЛОГИКА) начал работу")
    state_data = await state.get_data()
    start_time = time.monotonic()

    if call:
        # Режим 1: Нас вызвали нажатием на кнопку (call НЕ None)
        log.debug("Режим 1 (Callback)")
        # Мы получаем данные из хэндлера, который их распарсил
        char_id = explicit_char_id
        view_mode = explicit_view_mode
        call_type = explicit_call_type
        user_id = call.from_user.id

    else:
        # Режим 2: Нас вызвали из лобби (call=None)
        log.debug("Режим 2 (Лобби, call=None)")
        char_id = state_data.get("char_id")
        user_id = state_data.get("user_id")
        call_type = "bio"
        view_mode = "lobby"


        # --- Валидация ID ---
    if char_id is None:
        log.error(f"Ошибка: ID персонажа не найден.")
        if call: await error_int_id(call)
        return

    if user_id is None:
        log.error(f"Критическая ошибка: user_id не найден (Режим: {'Callback' if call else 'Лобби'}).")
        return

    # --- Инициализация Сервиса ---
    char_menu_service = CharacterMenuUIService(
        char_id=char_id,
        call_type=call_type,
        view_mode=view_mode
    )
    bd_data_status = state_data.get("bd_data_status") or None

    if bd_data_status is None or char_id != bd_data_status.get("id"):
        if bd_data_status is not None:
            log.warning(
            f"Кэш FSM неактуален. ID в FSM={char_id}, ID в кэше={bd_data_status.get('id')}. Принудительная перезагрузка.")
        bd_data_status = await get_status_data_package(char_id=char_id, user_id=user_id)

    if bd_data_status is None:
        log.warning(f"bd_data_status не найден для char_id={char_id}.")
        if call:  # Отвечаем на call, если он есть
            await error_msg_default(call)
        return

    # --- Подготовка сообщения ---
    message_content = state_data.get("message_content") or None

    character = await fsm_convector(bd_data_status.get("character"), "character")
    character_state = await fsm_convector(bd_data_status.get("character_stats"), "character_stats")

    text, kb = char_menu_service.staus_bio_message(
        character=character,
        stats=character_state,
    )

    log.debug(f"kb = {kb}")


    # --- Логика Отправки/Редактирования (ВОЗВРАЩЕННАЯ ВЕРСИЯ) ---
    try:
        new_message_created = False  # Флаг для отслеживания нового сообщения

        if message_content is None:
            # --- Случай 1: FSM пуст, сообщения нет ---
            log.debug("message_content=None. Требуется НОВОЕ сообщение.")

            if call:
                # Режим 1 (Callback): Создаем новое
                log.debug("Режим 1 (Callback): Отправляем новое через call.message.answer")
                msg = await call.message.answer(text=text, parse_mode='HTML', reply_markup=kb)

            elif user_id:
                # Режим 2 (Лобби): Создаем новое (Это тот самый случай из лога)
                log.debug(f"Режим 2 (Лобби): Отправляем новое через bot.send_message, chat_id={user_id}")
                msg = await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode='HTML',
                    reply_markup=kb
                )

            else:
                # Авария: некуда слать
                log.error("Критическая ошибка: 'message_content' is None, 'call' is None и 'user_id' is None.")
                return

                # Сохраняем данные *нового* сообщения в локальную переменную
            message_content = {
                "message_id": msg.message_id,
                "chat_id": msg.chat.id
            }
            new_message_created = True  # Ставим флаг

        else:
            # --- Случай 2: FSM не пуст, сообщение ЕСТЬ ---

            log.debug("message_content=Есть. РЕДАКТИРУЕМ существующее сообщение.")
            chat_id = message_content.get("chat_id")
            message_id = message_content.get("message_id")

            if not chat_id or not message_id:
                # Аварийный случай: FSM сломан. Пытаемся починить.
                log.error(f"Ошибка: message_content поврежден в FSM. {message_content}. Пытаемся починиться.")
                if call:
                    msg = await call.message.answer(text=text, parse_mode='HTML', reply_markup=kb)
                elif user_id:
                    msg = await bot.send_message(chat_id=user_id, text=text, parse_mode='HTML', reply_markup=kb)
                else:
                    log.error("Не можем починиться: нет 'call' и нет 'user_id'.")
                    return  # Не можем починиться

                message_content = {"message_id": msg.message_id, "chat_id": msg.chat.id}
                new_message_created = True
            else:
                # Штатное редактирование
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=TEXT_AWAIT,
                    parse_mode='HTML',

                )

                if start_time:
                    await await_min_delay(start_time, min_delay=1)

                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    parse_mode='HTML',
                    reply_markup=kb
                )


        update_data = {
            "bd_data_status": bd_data_status,
            "user_id" : user_id
        }

        if new_message_created:
            update_data["message_content"] = message_content

        await state.update_data(**update_data)

        log.info(f"status_menu_start_handler (ЛОГИКА) закончил свою работу ")

    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            log.debug("Сообщение не изменилось, игнорируем.")
        else:
            log.warning(f"Неожиданная ошибка Telegram API: {e}")
    except Exception as e:
        log.exception(f"Критическая ошибка при обновлении БИО/Статов: {e}")


@router.callback_query(
    StatusMenuCallback.filter(F.action == "bio"),  # <--- ФИЛЬТР ДЛЯ ФИЛЬТРА
    StateFilter(*FSM_CONTEX_CHARACTER_STATUS)
)
async def status_menu_callback_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        callback_data: StatusMenuCallback  # <--- Сюда придет ТОЛЬКО 'bio'
):
    """
    Хэндлер-обертка: Ловит callback ТОЛЬКО для action='bio'
    """
    log.debug(f"Получен [StatusMenuCallback(bio)]: {callback_data}")
    await call.answer()

    await call.message.edit_text(TEXT_AWAIT, parse_mode="html")



    await status_menu_start_handler(
        state=state,
        bot=bot,
        call=call,
        explicit_char_id=callback_data.char_id,
        explicit_view_mode=callback_data.view_mode,
        explicit_call_type=callback_data.action

    )