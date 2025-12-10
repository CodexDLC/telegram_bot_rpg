import contextlib

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.bot.resources.fsm_states.states import BugReport
from apps.bot.resources.keyboards.reply_kb import BUG_REPORT_BUTTON_TEXT, get_error_recovery_kb
from apps.bot.resources.texts.ui_messages import DEFAULT_ACTOR_NAME
from apps.common.services.report_service import ReportService

router = Router(name="bug_report_router")


@router.message(F.text == BUG_REPORT_BUTTON_TEXT)
async def start_bug_report_handler(m: Message, state: FSMContext) -> None:
    """Начинает FSM для отправки баг-репорта."""
    if not m.from_user:
        return
    user_id = m.from_user.id
    log.info(f"BugReport | status=started user_id={user_id}")

    with contextlib.suppress(TelegramAPIError):
        await m.delete()

    kb = InlineKeyboardBuilder()
    kb.button(text="🐞 Баг в логике", callback_data="bug_type:logic")
    kb.button(text="📝 Опечатка/текст", callback_data="bug_type:typo")
    kb.button(text="❌ Критический сбой", callback_data="bug_type:critical")
    kb.adjust(1)

    text = (
        f"<b>{DEFAULT_ACTOR_NAME}:</b> Вы выбрали режим отправки отчета.\n\n"
        f"Пожалуйста, выберите категорию, которая лучше всего описывает проблему:"
    )

    msg = await m.answer(text=text, parse_mode="html", reply_markup=kb.as_markup())

    await state.update_data(report_message_id=msg.message_id, report_chat_id=msg.chat.id)
    await state.set_state(BugReport.choosing_type)
    log.info(f"FSM | state=BugReport.choosing_type user_id={user_id}")


@router.callback_query(BugReport.choosing_type, F.data.startswith("bug_type:"))
async def choose_report_type_handler(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Обрабатывает выбор типа отчета и запрашивает текст."""
    if not call.data or not call.from_user:
        return
    await call.answer()
    user_id = call.from_user.id

    report_type_key = call.data.split(":")[-1]
    type_map = {"logic": "Баг в логике", "typo": "Опечатка/текст", "critical": "Критический сбой"}
    report_type_display = type_map.get(report_type_key, "Неизвестный")

    log.info(f"BugReport | type_selected='{report_type_display}' user_id={user_id}")

    state_data = await state.get_data()
    msg_id = state_data.get("report_message_id")
    chat_id = state_data.get("report_chat_id")

    text = (
        f"<b>{DEFAULT_ACTOR_NAME}:</b> Выбран тип: <b>{report_type_display}</b>.\n\n"
        f"Пожалуйста, опишите проблему максимально подробно. Просто отправьте "
        f"ваш отчет текстом (максимум 1000 символов). "
    )

    if msg_id and chat_id:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            parse_mode="html",
            reply_markup=None,
        )

    await state.update_data(report_type=report_type_display)
    await state.set_state(BugReport.awaiting_report_text)
    log.info(f"FSM | state=BugReport.awaiting_report_text user_id={user_id}")


@router.message(BugReport.awaiting_report_text, F.text)
async def process_report_text_handler(m: Message, state: FSMContext, bot: Bot) -> None:
    """Принимает текст отчета, отправляет его и завершает FSM."""
    if not m.from_user or not m.text:
        return
    user = m.from_user
    report_text = m.text[:1000].strip()

    log.info(f"BugReport | text_received_length={len(report_text)} user_id={user.id}")

    state_data = await state.get_data()
    report_type = state_data.get("report_type", "Не указан")
    msg_id = state_data.get("report_message_id")
    chat_id = state_data.get("report_chat_id")

    is_sent = await ReportService.send_report(
        bot=bot,
        user_id=user.id,
        username=user.username or user.first_name,
        report_type=report_type,
        report_text=report_text,
    )

    with contextlib.suppress(TelegramAPIError):
        await m.delete()

    final_text = ""
    if is_sent:
        final_text = f"<b>{DEFAULT_ACTOR_NAME}:</b> ✅ Ваш отчет '<b>{report_type}</b>' успешно отправлен. Спасибо!"
        log.info(f"BugReport | status=sent_successfully user_id={user.id}")
    else:
        final_text = (
            f"<b>{DEFAULT_ACTOR_NAME}:</b> ⚠️ Не удалось отправить отчет. "
            f"Проверьте, задан ли BUG_REPORT_CHANNEL_ID в .env."
        )
        log.warning(f"BugReport | status=send_failed user_id={user.id}")

    if msg_id and chat_id:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id, text=final_text, parse_mode="html", reply_markup=None
        )
    else:
        await m.answer(final_text, reply_markup=get_error_recovery_kb())

    await state.clear()
    log.info(f"FSM | action=clear reason=bug_report_finished user_id={user.id}")
