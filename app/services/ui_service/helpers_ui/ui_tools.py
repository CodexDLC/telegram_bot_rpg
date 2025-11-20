# app/services/ui_service/helpers_ui/ui_tools.py
import asyncio
import time

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
