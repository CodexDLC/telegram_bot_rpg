import asyncio
import time
from collections.abc import Awaitable, Callable

from loguru import logger as log


class SmartWorker:
    """
    Умный воркер для выполнения периодических задач с выравниванием времени (Tick Rate).
    Гарантирует, что задачи запускаются не чаще, чем раз в `interval` секунд,
    но и не реже (если задачи выполняются быстро).
    """

    def __init__(self, interval: float, task_name: str = "Worker"):
        self.interval = interval  # Целевое время цикла (например, 1.0 сек)
        self.task_name = task_name
        self.is_running = False

    async def run(self, *tasks: Callable[[], Awaitable[None]]) -> None:
        """
        Запускает бесконечный цикл, который выполняет переданные функции
        и выравнивает время сна.

        Args:
            *tasks: Асинхронные функции (без аргументов), которые нужно выполнять в каждом тике.
        """
        self.is_running = True
        log.info(f"🔄 [{self.task_name}] Started. Target Interval: {self.interval}s")

        while self.is_running:
            # 1. Засекаем время начала тика (используем perf_counter для точности)
            start_time = time.perf_counter()

            try:
                # 2. Запускаем все задачи ПАРАЛЛЕЛЬНО
                # Мы вызываем функции task(), так как передаем их как объекты
                await asyncio.gather(*(task() for task in tasks))

            except Exception as e:  # noqa: BLE001
                # Если упало — не крашим весь воркер, просто пишем лог
                # Мы намеренно ловим все ошибки, чтобы воркер жил вечно
                log.exception(f"❌ [{self.task_name}] Error in tick: {e}")

            # 3. Считаем, сколько времени потратили
            elapsed_time = time.perf_counter() - start_time

            # 4. Вычисляем время сна
            sleep_time = self.interval - elapsed_time

            # Логика "Лага": если работали дольше, чем интервал
            if sleep_time < 0:
                lag = abs(sleep_time)
                log.warning(f"⚠️ [{self.task_name}] Overload! Took {elapsed_time:.3f}s (Lag: {lag:.3f}s)")
                # Спим 0 (передаем управление event loop, чтобы другие процессы дышали)
                await asyncio.sleep(0)
            else:
                # Всё ок, спим остаток времени
                await asyncio.sleep(sleep_time)

    def stop(self) -> None:
        """Останавливает воркер после завершения текущего тика."""
        self.is_running = False
        log.info(f"🛑 [{self.task_name}] Stopping...")
