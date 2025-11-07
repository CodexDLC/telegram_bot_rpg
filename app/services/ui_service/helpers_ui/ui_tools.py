import asyncio
import time
import logging
from typing import Dict, Tuple, Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

log = logging.getLogger(__name__)


async def await_min_delay(start_time: float, min_delay: float = 0.5):
    """
    Обеспечивает минимальную задержку для асинхронных операций.

    Эта функция полезна для UI, чтобы предотвратить слишком быстрые
    обновления сообщений, которые могут выглядеть как мерцание. Она
    вычисляет время, прошедшее с `start_time`, и если оно меньше
    `min_delay`, асинхронно "спит" оставшееся время.

    Args:
        start_time (float): Время начала операции (обычно `time.monotonic()`).
        min_delay (float, optional): Минимальная желаемая задержка
            в секундах. Defaults to 0.5.

    Returns:
        None
    """
    elapsed_time = time.monotonic() - start_time
    if elapsed_time < min_delay:
        sleep_duration = min_delay - elapsed_time
        log.debug(f"Операция быстрая ({elapsed_time:.2f}с). Ожидание: {sleep_duration:.2f}с.")
        await asyncio.sleep(sleep_duration)


async def animate_message_sequence(
        message_to_edit: Dict[str, int],
        sequence: Tuple[Tuple[str, int], ...],
        bot: Bot,
        final_reply_markup: Optional[InlineKeyboardMarkup] = None
):
    """
    Анимирует сообщение, последовательно редактируя его текст.

    Эта функция принимает кортеж "кадров" (текст и задержка) и
    последовательно обновляет одно и то же сообщение, создавая эффект
    анимации или печатания текста. Клавиатура (`final_reply_markup`)
    добавляется только на последнем шаге.

    Args:
        message_to_edit (Dict[str, int]): Словарь с `chat_id` и `message_id`
            сообщения, которое нужно анимировать.
        sequence (Tuple[Tuple[str, int], ...]): Кортеж, где каждый элемент
            является кортежем из (text_line, pause_duration).
        bot (Bot): Экземпляр бота для отправки запросов к API.
        final_reply_markup (Optional[InlineKeyboardMarkup], optional):
            Клавиатура, которая будет добавлена к сообщению на
            последнем шаге анимации. Defaults to None.

    Returns:
        None
    """
    total_steps = len(sequence)
    for i, (text_line, pause_duration) in enumerate(sequence):
        is_last_step = (i == total_steps - 1)
        # Клавиатура добавляется только на последнем шаге, чтобы пользователь
        # не мог нажать на кнопки до завершения анимации.
        markup = final_reply_markup if is_last_step else None

        await bot.edit_message_text(
            chat_id=message_to_edit.get("chat_id"),
            message_id=message_to_edit.get("message_id"),
            text=text_line,
            parse_mode='HTML',
            reply_markup=markup
        )
        # Пауза перед следующим "кадром" анимации.
        if not is_last_step:
            await asyncio.sleep(pause_duration)
