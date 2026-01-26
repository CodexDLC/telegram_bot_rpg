import asyncio
from collections.abc import Callable
from typing import Any

from game_client.telegram_bot.services.sender.view_sender import ViewSender


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
        2. Добавляет анимацию к контенту (заменяет {ANIMATION} или добавляет в конец).
        3. Отправляет через sender.
        4. Если !is_waiting -> выходит.
        """
        steps = int(timeout / step_delay)

        for i in range(steps):
            # 1. Запрос данных
            result = await check_func()

            # Разбираем результат
            if isinstance(result, tuple):
                view_dto, is_waiting = result
            else:
                view_dto = result
                is_waiting = False

            # 2. Добавляем анимацию
            if is_waiting and view_dto.content:
                anim_str = self._get_animation_frame(i)

                if "{ANIMATION}" in view_dto.content.text:
                    view_dto.content.text = view_dto.content.text.replace("{ANIMATION}", anim_str)
                else:
                    view_dto.content.text += f"\n\n{anim_str}"

            # 3. Отправка
            await self.sender.send(view_dto)

            # 4. Выход
            if not is_waiting:
                return

            await asyncio.sleep(step_delay)

    def _get_animation_frame(self, step: int) -> str:
        """Генерирует строку анимации (полоска)."""
        total_frames = 10
        filled = step % (total_frames + 1)
        empty = total_frames - filled

        bar = "■" * filled + "□" * empty
        return f"⏳ <b>Ожидание хода</b> [{bar}]"
