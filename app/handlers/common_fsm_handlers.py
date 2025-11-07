import logging
from aiogram import Router, F
from aiogram.types import Message

from app.resources.fsm_states.states import StartTutorial, CharacterCreation, CharacterLobby, GARBAGE_TEXT_STATES

log = logging.getLogger(__name__)

router = Router(name="common_fsm_router")


@router.message(F.text, *GARBAGE_TEXT_STATES)
async def delete_garbage_text(m: Message):
    """
    Удаляет нежелательные текстовые сообщения в определенных состояниях FSM.

    Этот обработчик отлавливает любые текстовые сообщения, которые пользователь
    может отправить, когда бот ожидает нажатие на inline-кнопку (а не ввод
    текста). Это предотвращает "засорение" чата и возможные неверные
    срабатывания других обработчиков.

    Args:
        m (Message): Входящее "мусорное" сообщение от пользователя.

    Returns:
        None
    """
    try:
        # Просто удаляем сообщение, чтобы оно не мешало.
        await m.delete()
    except Exception as e:
        log.warning(f"Не удалось удалить 'мусорное' сообщение: {e}")
