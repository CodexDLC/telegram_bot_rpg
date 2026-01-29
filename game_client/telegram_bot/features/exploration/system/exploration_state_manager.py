# game_client/telegram_bot/features/exploration/system/exploration_state_manager.py

import time
from typing import Any

from aiogram.fsm.context import FSMContext


class ExplorationStateManager:
    """
    Управляет состоянием исследования в FSM.
    Используется для хранения временных данных во время поллинга (перемещения).
    """

    KEY_START_TIME = "expl_move_start"
    KEY_RESULT = "expl_move_result"
    KEY_DURATION = "expl_move_duration"

    def __init__(self, state: FSMContext):
        self.state = state

    async def start_move(self):
        """Запоминает время начала перемещения."""
        await self.state.update_data({self.KEY_START_TIME: time.time()})
        # Очищаем старые результаты
        data = await self.state.get_data()
        if self.KEY_RESULT in data:
            # Не удаляем ключ, а ставим None, или используем update_data
            # FSM aiogram не имеет метода delete_data для ключа, только set_data
            # Поэтому просто перезаписываем
            await self.state.update_data({self.KEY_RESULT: None, self.KEY_DURATION: 0})

    async def set_move_result(self, result: Any, duration: float = 0):
        """Сохраняет результат запроса к бэкенду."""
        await self.state.update_data({self.KEY_RESULT: result, self.KEY_DURATION: duration})

    async def get_move_status(self) -> tuple[Any | None, float, float]:
        """
        Возвращает статус перемещения.
        Returns:
            (result, elapsed_time, required_duration)
            result: DTO ответа или None (если еще не пришел)
            elapsed_time: Сколько времени прошло с начала
            required_duration: Сколько нужно ждать (из ответа бэкенда)
        """
        data = await self.state.get_data()
        start_time = data.get(self.KEY_START_TIME, time.time())
        result = data.get(self.KEY_RESULT)
        duration = data.get(self.KEY_DURATION, 0)

        elapsed = time.time() - start_time
        return result, elapsed, duration

    async def clear_move_data(self):
        """Очищает данные перемещения."""
        # Можно не очищать, они перезапишутся при следующем start_move
        pass
