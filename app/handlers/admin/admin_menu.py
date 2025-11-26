from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger as log

from app.filters.is_admin import IsAdmin
from app.resources.fsm_states.states import AdminMode

# Создаем роутер и сразу вешаем на него фильтр админа
# Теперь все хэндлеры в этом роутере доступны ТОЛЬКО админам
router = Router(name="admin_router")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("admin"))
async def admin_start_handler(m: Message, state: FSMContext):
    """Точка входа в админку."""
    if m.from_user:
        log.info(f"Admin {m.from_user.id} accessed admin panel.")

    await state.clear()
    await state.set_state(AdminMode.menu)

    text = "<b>🛠 Панель Администратора (God Mode)</b>\nВыберите инструмент:"
    kb = _get_admin_kb()

    await m.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(AdminMode.menu, F.data == "admin:close")
async def admin_close_handler(call: CallbackQuery, state: FSMContext):
    """Выход из админки."""
    await state.clear()
    if isinstance(call.message, Message):
        await call.message.delete()
    await call.answer("Режим админа деактивирован.")


# --- Вспомогательные методы ---


def _get_admin_kb():
    kb = InlineKeyboardBuilder()

    # Пока сделаем кнопки-заглушки (мы реализуем логику в следующем шаге)
    kb.button(text="📦 Выдать Предмет", callback_data="admin:item")
    kb.button(text="💰 Насыпать Ресурсов", callback_data="admin:resource")
    kb.button(text="🌀 Телепорт", callback_data="admin:teleport")
    kb.button(text="💀 Вайп (Себя)", callback_data="admin:wipe_self")

    kb.adjust(1)

    kb.row(InlineKeyboardButton(text="❌ Закрыть панель", callback_data="admin:close"))
    return kb.as_markup()
