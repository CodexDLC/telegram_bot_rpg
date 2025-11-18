import contextlib

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

# Импорты для FSM, кнопок и сервисов
from app.resources.fsm_states.states import BugReport
from app.resources.keyboards.reply_kb import BUG_REPORT_BUTTON_TEXT, get_error_recovery_kb
from app.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from app.services.report_service import ReportService

router = Router(name="bug_report_router")


# ================================================================
# 1. Хэндлер: Начало отчета (по кнопке "🐞 Сообщить об ошибке")
# ================================================================
@router.message(F.text == BUG_REPORT_BUTTON_TEXT)
async def start_bug_report_handler(m: Message, state: FSMContext) -> None:
    """Обрабатывает нажатие Reply-кнопки и начинает FSM с выбором типа отчета."""
    if not m.from_user:
        return
    log.info(f"User {m.from_user.id} начал создание баг-репорта.")

    # 1. Удаляем сообщение с командой/кнопкой, чтобы не засорять чат
    with contextlib.suppress(TelegramAPIError):
        await m.delete()
        log.warning(f"Не удалось удалить сообщение {m.message_id}")

    # 2. Формируем клавиатуру для выбора типа
    kb = InlineKeyboardBuilder()
    kb.button(text="🐞 Баг в логике", callback_data="bug_type:logic")
    kb.button(text="📝 Опечатка/текст", callback_data="bug_type:typo")
    kb.button(text="❌ Критический сбой", callback_data="bug_type:critical")
    kb.adjust(1)

    text = (
        f"<b>{DEFAULT_ACTOR_NAME}:</b> Вы выбрали режим отправки отчета.\n\n"
        f"Пожалуйста, выберите категорию, которая лучше всего описывает проблему:"
    )

    # 3. Отправляем сообщение и сохраняем его ID для редактирования
    msg = await m.answer(text=text, parse_mode="html", reply_markup=kb.as_markup())

    await state.update_data(report_message_id=msg.message_id, report_chat_id=msg.chat.id)
    await state.set_state(BugReport.choosing_type)
    log.info(f"User {m.from_user.id} переведен в состояние BugReport.choosing_type.")


# ================================================================
# 2. Хэндлер: Выбор типа отчета (Callback)
# ================================================================
@router.callback_query(BugReport.choosing_type, F.data.startswith("bug_type:"))
async def choose_report_type_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Обрабатывает выбор типа отчета и переводит в ожидание текста."""
    if not call.data or not call.from_user:
        return
    await call.answer()

    # 1. Определяем тип отчета
    report_type_key = call.data.split(":")[-1]
    type_map = {"logic": "Баг в логике", "typo": "Опечатка/текст", "critical": "Критический сбой"}
    report_type_display = type_map.get(report_type_key, "Неизвестный")

    log.info(f"User {call.from_user.id} выбрал тип отчета: {report_type_display}")

    state_data = await state.get_data()
    msg_id = state_data.get("report_message_id")
    chat_id = state_data.get("report_chat_id")

    # 2. Формируем запрос на ввод текста
    text = (
        f"<b>{DEFAULT_ACTOR_NAME}:</b> Выбран тип: <b>{report_type_display}</b>.\n\n"
        f"Пожалуйста, опишите проблему максимально подробно. Просто отправьте "
        f"ваш отчет текстом (максимум 1000 символов). "
    )

    # 3. Редактируем сообщение (убираем кнопки)
    if msg_id and chat_id:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            parse_mode="html",
            reply_markup=None,  # Убираем кнопки
        )

    # 4. Обновляем FSM
    await state.update_data(report_type=report_type_display)
    await state.set_state(BugReport.awaiting_report_text)
    log.info(f"User {call.from_user.id} переведен в состояние BugReport.awaiting_report_text.")


# ================================================================
# 3. Хэндлер: Обработка текста отчета и отправка (Message)
# ================================================================
@router.message(BugReport.awaiting_report_text, F.text)
async def process_report_text_handler(m: Message, state: FSMContext, bot: Bot) -> None:
    """Принимает текст отчета, отправляет его в канал и завершает FSM."""
    if not m.from_user or not m.text:
        return
    user = m.from_user
    report_text = m.text[:1000].strip()  # Обрезаем текст

    log.info(f"User {user.id} отправил текст баг-репорта (длина: {len(report_text)}).")

    state_data = await state.get_data()
    report_type = state_data.get("report_type", "Не указан")
    msg_id = state_data.get("report_message_id")
    chat_id = state_data.get("report_chat_id")

    # 1. Вызываем сервис для отправки отчета
    is_sent = await ReportService.send_report(
        bot=bot,
        user_id=user.id,
        username=user.username or user.first_name,
        report_type=report_type,
        report_text=report_text,
    )

    # 2. Удаляем сообщение с текстом отчета, чтобы не дублировать
    with contextlib.suppress(Exception):
        await m.delete()

    # 3. Формируем финальное сообщение для пользователя
    final_text = ""
    if is_sent:
        final_text = f"<b>{DEFAULT_ACTOR_NAME}:</b> ✅ Ваш отчет '<b>{report_type}</b>' успешно отправлен. Спасибо!"
    else:
        final_text = (
            f"<b>{DEFAULT_ACTOR_NAME}:</b> ⚠️ Не удалось отправить отчет. "
            f"Проверьте, задан ли BUG_REPORT_CHANNEL_ID в .env."
        )

    # 4. Редактируем сообщение FSM или отправляем новое (если старого нет)
    if msg_id and chat_id:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id, text=final_text, parse_mode="html", reply_markup=None
        )
    else:
        await m.answer(final_text, reply_markup=get_error_recovery_kb())

    # 5. Очищаем состояние FSM
    await state.clear()
    log.info(f"FSM для user {user.id} очищен после отправки отчета.")
