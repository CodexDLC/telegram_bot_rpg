import asyncio # (убедись, что импорты есть)
import time
import logging

from aiogram import Bot
from aiogram.types import Message

log = logging.getLogger(__name__)



async def await_min_delay(start_time: float, min_delay: float = 0.5):
    """
    Проверяет, сколько времени прошло, и "спит"
    недостающее время, чтобы гарантировать 'min_delay'.
    """
    elapsed_time = time.monotonic() - start_time
    if elapsed_time < min_delay:
        log.debug(f"Логика быстрая ({elapsed_time:.2f}с). Ждем {min_delay - elapsed_time:.2f}с.")
        await asyncio.sleep(min_delay - elapsed_time)


async def animate_message_sequence(
        message_to_edit: dict[str, int],
        sequence: tuple[tuple[str, int], ...],
        bot: Bot,
        final_reply_markup=None
):
    """
    Анимирует сообщение, редактируя его по шагам из 'sequence'.
    """
    total_steps = len(sequence)
    for i, (text_line, pause_duration) in enumerate(sequence):
        is_last_step = (i == total_steps - 1)
        markup = final_reply_markup if is_last_step else None

        await bot.edit_message_text(
            chat_id=message_to_edit.get("chat_id"),
            message_id=message_to_edit.get("message_id"),
            text=text_line,
            parse_mode='HTML',
            reply_markup=markup
        )
        await asyncio.sleep(pause_duration)