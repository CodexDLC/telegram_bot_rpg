# app/handlers/callback/ui/status_menu/character_modifier.py
import logging
import time

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.resources.fsm_states.states import FSM_CONTEX_CHARACTER_STATUS
from app.resources.keyboards.status_callback import StatusModifierCallback

log = logging.getLogger(__name__)

router = Router(name="character_Modifier_menu")


@router.callback_query(StatusModifierCallback.filter(F.level == "group"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_modifier_group_handler(
        call: CallbackQuery,
        state: FSMContext,
        bot: Bot,
        callback_data: StatusModifierCallback
) -> None:
    """
    Обрабатывает выбор группы навыков, отображая навыки в этой группе.

    Args:
        call (CallbackQuery): Callback от кнопки выбора группы.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (StatusModifierCallback): Данные из callback.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'character_skill_group_handler' получил обновление без 'from_user'.")
        return




@router.callback_query(StatusModifierCallback.filter(F.level == "detail"),
                       StateFilter(*FSM_CONTEX_CHARACTER_STATUS))
async def character_modifier_detail_handler(call: CallbackQuery, state: FSMContext, bot: Bot, callback_data: StatusModifierCallback) -> None:
    """
    Обрабатывает выбор конкретного навыка (заглушка).

    Args:
        call (CallbackQuery): Callback от кнопки выбора навыка.
        state (FSMContext): Состояние FSM.
        bot (Bot): Экземпляр бота.
        callback_data (StatusModifierCallback): Данные из callback.

    Returns:
        None
    """
    if not call.from_user:
        log.warning("Хэндлер 'character_skill_handler' получил обновление без 'from_user'.")
        return
