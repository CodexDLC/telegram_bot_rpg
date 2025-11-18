# app/services/ui_service/helpers_ui/ui_tools.py
import asyncio
import time

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup
from loguru import logger as log


async def await_min_delay(start_time: float, min_delay: float = 0.5) -> None:
    """
    Обеспечивает минимальную задержку для асинхронных операций.

    Полезна для UI, чтобы предотвратить слишком быстрые обновления сообщений,
    которые могут выглядеть как мерцание. Вычисляет время, прошедшее с
    `start_time`, и если оно меньше `min_delay`, асинхронно "спит"
    оставшееся время.

    Args:
        start_time (float): Время начала операции (`time.monotonic()`).
        min_delay (float): Минимальная желаемая задержка в секундах.
    """
    elapsed_time = time.monotonic() - start_time
    if elapsed_time < min_delay:
        sleep_duration = min_delay - elapsed_time
        log.debug(f"Операция заняла {elapsed_time:.3f}с. Принудительная задержка: {sleep_duration:.3f}с.")
        await asyncio.sleep(sleep_duration)
    else:
        log.debug(f"Операция заняла {elapsed_time:.3f}с. Дополнительная задержка не требуется.")


async def animate_message_sequence(
    message_to_edit: dict[str, int],
    sequence: tuple[tuple[str, float], ...],
    bot: Bot,
    final_reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """
    Анимирует сообщение, последовательно редактируя его текст.

    Принимает кортеж "кадров" (текст и задержка) и последовательно
    обновляет одно и то же сообщение. Клавиатура (`final_reply_markup`)
    добавляется только на последнем шаге.

    Args:
        message_to_edit (Dict[str, int]): Словарь с `chat_id` и `message_id`.
        sequence (Tuple[Tuple[str, float], ...]): Кортеж, где каждый элемент -
            это (`text_line`, `pause_duration`).
        bot (Bot): Экземпляр бота.
        final_reply_markup (Optional[InlineKeyboardMarkup]): Клавиатура для
            финального сообщения.
    """
    if not message_to_edit:
        log.error("Попытка анимировать сообщение, но 'message_to_edit' не предоставлен.")
        return

    chat_id = message_to_edit.get("chat_id")
    message_id = message_to_edit.get("message_id")
    total_steps = len(sequence)
    log.debug(f"Начало анимации сообщения {message_id} в чате {chat_id} ({total_steps} шагов).")

    for i, (text_line, pause_duration) in enumerate(sequence):
        is_last_step = i == total_steps - 1
        markup = final_reply_markup if is_last_step else None

        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text_line, parse_mode="HTML", reply_markup=markup
            )
            log.debug(f"Шаг {i + 1}/{total_steps} анимации выполнен.")
        except TelegramBadRequest as e:
            # Игнорируем ошибку, если сообщение не изменилось, но логируем остальные.
            if "message is not modified" in str(e).lower():
                log.debug("Сообщение на шаге анимации не изменилось, пропуск.")
            else:
                log.warning(f"Ошибка Telegram API при анимации сообщения: {e}")
                # Прерываем анимацию в случае серьезной ошибки.
                break
        except TelegramAPIError as e:
            log.exception(f"Критическая ошибка при анимации сообщения: {e}")
            break

        if not is_last_step:
            await asyncio.sleep(pause_duration)

    log.info(f"Анимация сообщения {message_id} в чате {chat_id} завершена.")
