import asyncio # (убедись, что импорты есть)
import time
import logging

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