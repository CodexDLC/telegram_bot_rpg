# app/handlers/fsn_callback/char_creation.py
import asyncio
import logging
from aiogram import Router, F, Bot

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.resources.fsm_states.states import StartTutorial
from app.resources.keyboards.inline_kb.loggin_und_new_character import tutorial_kb
from app.resources.texts.game_messages.tutorial_messages import TutorialMessages

log = logging.getLogger(__name__)

router = Router(name="character_creation_fsm")



@router.callback_query(StartTutorial.start, F.data.startswith("tut:"))
async def start_tutorial(call: CallbackQuery, state: FSMContext):
    """
        Старт tutorial.
    """
    await call.answer()

    data = await state.get_data()
    char_id = data.get("character_id")


