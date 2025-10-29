import logging
from aiogram import Router, F
from aiogram.types import Message

from app.resources.fsm_states.states import StartTutorial, CharacterCreation

log = logging.getLogger(__name__)

router = Router(name="common_fsm_router")

GARBAGE_TEXT_STATES = [
    StartTutorial,  # Весь класс (start, in_progress, confirmation)
    CharacterCreation.choosing_gender,  # Конкретное состояние
    CharacterCreation.confirm         # Конкретное состояние
]



@router.message(F.text, *GARBAGE_TEXT_STATES)
async def delete_garbage_text(m: Message):
    """
    Этот хэндлер ловит ЛЮБОЙ "мусорный" текст во всех состояниях,
    перечисленных в GARBAGE_TEXT_STATES, и просто удаляет его.
    """
    try:
        await m.delete()
    except Exception as e:
        log.warning(f"Не удалось удалить 'мусорное' сообщение: {e}")