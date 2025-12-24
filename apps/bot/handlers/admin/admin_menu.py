# MARKED: Uses non-InGame state: AdminMode
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from apps.bot.resources.fsm_states.states import AdminMode
from apps.bot.utils.filters.is_admin import IsAdmin

# Все хэндлеры в этом роутере доступны только администраторам.
router = Router(name="admin_router")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("admin"))
async def admin_start_handler(m: Message, state: FSMContext):
    """Точка входа в панель администратора."""
    user_id = m.from_user.id if m.from_user else "N/A"
    log.info(f"AdminPanel | status=accessed user_id={user_id}")

    await state.clear()
    await state.set_state(AdminMode.menu)

    text = "<b>🛠 Панель Администратора (God Mode)</b>\nВыберите инструмент:"
    kb = _get_admin_kb()

    await m.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(AdminMode.menu, F.data == "admin:close")
async def admin_close_handler(call: CallbackQuery, state: FSMContext):
    """Обрабатывает выход из панели администратора."""
    user_id = call.from_user.id
    log.info(f"AdminPanel | status=closed user_id={user_id}")
    await state.clear()
    if isinstance(call.message, Message):
        await call.message.delete()
    await call.answer("Режим админа деактивирован.")


def _get_admin_kb():
    """Возвращает клавиатуру с кнопками админ-панели."""
    kb = InlineKeyboardBuilder()

    # TODO: Реализовать логику для кнопок-заглушек.
    kb.button(text="📦 Выдать Предмет", callback_data="admin:item")
    kb.button(text="💰 Насыпать Ресурсов", callback_data="admin:resource")
    kb.button(text="🌀 Телепорт", callback_data="admin:teleport")
    kb.button(text="💀 Вайп (Себя)", callback_data="admin:wipe_self")

    kb.adjust(1)

    kb.row(InlineKeyboardButton(text="❌ Закрыть панель", callback_data="admin:close"))
    return kb.as_markup()
