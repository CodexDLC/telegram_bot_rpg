import asyncio
from collections.abc import Callable
from typing import Any

from apps.bot.ui_service.view_sender import ViewSender


class UIAnimationService:
    """
    Сервис для анимации ожидания (Polling).
    Работает поверх ViewSender.
    """

    def __init__(self, sender: ViewSender):
        self.sender = sender

    async def start_combat_polling(
        self,
        check_func: Callable[[], Any],  # Возвращает (UnifiedViewDTO, is_waiting)
        timeout: int = 60,
        step_delay: float = 2.0,
    ) -> None:
        """
        Запускает цикл поллинга для боя.
        Каждые step_delay секунд:
        1. Запрашивает статус через check_func.
        2. Добавляет анимацию к контенту.
        3. Отправляет через sender.
        4. Если !is_waiting -> выходит.
        """
        steps = int(timeout / step_delay)

        for i in range(steps):
            # 1. Запрос данных
            # check_func должна возвращать (view_dto, is_waiting)
            # Или view_dto должен содержать флаг.
            # Предположим, check_func возвращает UnifiedViewDTO, а статус мы проверяем внутри
            # Но лучше, чтобы check_func возвращала кортеж, чтобы сервис не гадал.

            result = await check_func()

            # Разбираем результат
            if isinstance(result, tuple):
                view_dto, is_waiting = result
            else:
                # Fallback
                view_dto = result
                is_waiting = False  # Если вернул просто DTO, считаем что готово? Или наоборот?
                # Договоримся: check_func возвращает (UnifiedViewDTO, is_waiting)

            # 2. Добавляем анимацию
            if is_waiting and view_dto.content:
                anim_str = self._get_animation_frame(i)
                # Добавляем к тексту (предполагаем, что там есть место)
                view_dto.content.text += f"\n\n{anim_str}"

            # 3. Отправка
            await self.sender.send(view_dto)

            # 4. Выход
            if not is_waiting:
                return

            await asyncio.sleep(step_delay)

        # Timeout
        # Можно отправить сообщение об ошибке, если нужно

    def _get_animation_frame(self, step: int) -> str:
        """Генерирует строку анимации (полоска)."""
        total_frames = 10
        filled = step % (total_frames + 1)
        empty = total_frames - filled

        bar = "■" * filled + "□" * empty
        return f"⏳ <b>Ожидание хода</b> [{bar}]"
