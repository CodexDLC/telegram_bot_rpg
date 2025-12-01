import asyncio
import contextlib
import random
from collections.abc import Awaitable, Callable

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from loguru import logger as log

from app.resources.schemas_dto.fsm_state_dto import SessionDataDTO


class UIAnimationService:
    """
    Единый сервис для всех UI-анимаций: прогресс-бары, таймеры, сюжетные сцены.
    """

    def __init__(self, bot: Bot, message_data: SessionDataDTO):
        self.bot = bot
        # Защита: если message_content еще нет (например, начало диалога),
        # берем пустой dict, чтобы не упасть на .get()
        content = message_data.message_content or {}
        self.chat_id = content.get("chat_id")
        self.message_id = content.get("message_id")

    async def _render_frame(self, text: str, kb=None) -> None:
        """Приватный метод отрисовки кадра."""
        if not self.chat_id or not self.message_id:
            log.warning("UIAnimationService: нет координат сообщения (chat_id/message_id).")
            return

        with contextlib.suppress(TelegramBadRequest):
            await self.bot.edit_message_text(
                chat_id=self.chat_id, message_id=self.message_id, text=text, reply_markup=kb, parse_mode="HTML"
            )

    # --- 1. ЗАМЕНА СТАРОГО ХЕЛПЕРА (Сюжетные вставки) ---
    async def animate_sequence(self, sequence: tuple[tuple[str, float], ...], final_kb=None) -> None:
        """
        Проигрывает готовую последовательность кадров (текст, пауза).
        Используется в Туториале (WAKING_UP_SEQUENCE) и создании персонажа.
        """
        total_steps = len(sequence)

        for i, (text_line, pause_duration) in enumerate(sequence):
            is_last = i == total_steps - 1
            # Клавиатуру цепляем только на последний кадр
            kb = final_kb if is_last else None

            await self._render_frame(text_line, kb)

            if not is_last:
                await asyncio.sleep(pause_duration)

    # --- 2. НАВИГАЦИЯ (Прогресс-бар) ---
    async def animate_navigation(self, duration: float, flavor_texts: list[str]) -> None:
        remaining_time = int(duration)
        current_flavor = random.choice(flavor_texts)
        header = "👣 <b>В пути...</b>"

        try:
            while remaining_time > 0:
                progress_bar = self._generate_progress_bar(duration, remaining_time)
                frame_text = (
                    f"{header}\n<i>{current_flavor}</i>\n\n⏳ <code>[{progress_bar}] {remaining_time} сек.</code>"
                )
                await self._render_frame(frame_text)
                await asyncio.sleep(1)
                remaining_time -= 1
        except TelegramBadRequest as e:
            log.warning(f"Ошибка анимации навигации: {e}")

    # --- 3. ДЕЙСТВИЯ (Крафт, Сбор - динамический текст) ---
    async def animate_action(self, duration: float, action_name: str, flavor_texts: str | list[str]) -> None:
        remaining_time = int(duration)
        header = f"🛠 <b>{action_name}...</b>"

        if isinstance(flavor_texts, str):
            flavor_texts = [flavor_texts]

        try:
            while remaining_time > 0:
                # Тут текст меняется каждый тик!
                current_flavor = random.choice(flavor_texts)
                progress_bar = self._generate_progress_bar(duration, remaining_time)

                frame_text = (
                    f"{header}\n<i>{current_flavor}</i>\n\n⏳ <code>[{progress_bar}] {remaining_time} сек.</code>"
                )
                await self._render_frame(frame_text)
                await asyncio.sleep(1)
                remaining_time -= 1
        except TelegramBadRequest as e:
            log.warning(f"Ошибка анимации действия: {e}")

    # --- 4. УНИВЕРСАЛЬНАЯ ЗАГРУЗКА (Замена TEXT_AWAIT) ---
    async def animate_loading(self, duration: float = 2.0, text: str = "⏳ Обработка данных...") -> None:
        """
        Проигрывает анимацию загрузки с прогресс-баром.
        Идеально подходит для замены статичных заглушек типа TEXT_AWAIT.

        :param duration: Длительность анимации в секундах.
        :param text: Текст, который будет висеть над баром.
        """
        remaining_time = int(duration)

        try:
            while remaining_time > 0:
                # Генерируем полоску (используем наш метод)
                progress_bar = self._generate_progress_bar(duration, remaining_time)

                # Формируем кадр
                frame_text = f"{text}\n\n🚀 <code>[{progress_bar}] {remaining_time}c.</code>"

                # Рисуем
                await self._render_frame(frame_text)

                # Ждем
                await asyncio.sleep(1)
                remaining_time -= 1

        except TelegramBadRequest as e:
            log.warning(f"Ошибка анимации загрузки: {e}")

    def _generate_progress_bar(self, total_time: float, remaining: int, max_len: int = 10) -> str:
        """
        Генерирует строку прогресс-бара.
        Если total_time < max_len, длина бара равна времени (в секундах).
        Если total_time > max_len, бар масштабируется до max_len.
        """
        # Базовый расчет (без масштабирования)
        raw_filled = int(total_time) - remaining

        if total_time > max_len:
            # Масштабирование (для длинных действий)
            scale = max_len / total_time
            filled = int(raw_filled * scale)
            empty = max_len - filled
        else:
            # Без масштабирования (для коротких действий)
            filled = raw_filled
            empty = remaining

        # Защита от отрицательных чисел (на всякий случай)
        filled = max(0, filled)
        empty = max(0, empty)

        return "■" * filled + "□" * empty

    async def animate_polling(
        self,
        base_text: str,
        check_func: Callable[[], Awaitable[str | None]],
        steps: int = 6,
        step_delay: float = 5.0,
        fixed_duration: bool = False,
    ) -> str | None:
        """
        Универсальный цикл ожидания с анимацией.

        Args:
            base_text: Текст сообщения (например, "🔎 Поиск противника").
            check_func: Асинхронная функция, возвращающая session_id (если бой найден) или None.
            steps: Количество итераций (по умолчанию 6 шагов * 5 сек = 30 сек).
            step_delay: Задержка между шагами.
            fixed_duration: Если True, цикл не прервется раньше времени, даже если бой найден
                            (бой начнется только в конце анимации).

        Returns:
            str: session_id (если найден) или None (если таймаут).
        """

        found_result = None

        for i in range(1, steps + 1):
            # 1. Рисуем прогресс
            # Пример: [■■□□□□] 10/30 сек
            prog_bar = "■" * i + "□" * (steps - i)
            elapsed = int(i * step_delay)
            total_time = int(steps * step_delay)

            frame_text = f"{base_text}\n\n⏳ <code>[{prog_bar}] {elapsed}/{total_time} с.</code>"

            # Обновляем UI (игнорируем ошибку "не изменилось")
            await self._render_frame(frame_text)

            # 2. Проверка (если еще не нашли)
            if not found_result:
                found_result = await check_func()

            # 3. Логика выхода
            if found_result and not fixed_duration:
                # Если бой найден и нам не нужно ждать до конца -> выходим сразу
                # Но даем маленькую паузу (1 сек), чтобы юзер увидел прогресс
                await asyncio.sleep(1)
                return found_result

            # 4. Спим до следующего шага
            await asyncio.sleep(step_delay)

        # Если цикл закончился, возвращаем то, что нашли (или None)
        return found_result
