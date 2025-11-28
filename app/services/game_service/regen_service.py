import time
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.core_service.manager.account_manager import account_manager
from app.services.game_service.stats_aggregation_service import StatsAggregationService


class RegenService:
    """
    Сервис "Ленивого восстановления" (Lazy Regeneration).
    Вычисляет изменение HP/Energy на основе прошедшего времени.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        # Используем агрегатор, чтобы знать МАКСИМАЛЬНЫЕ значения и СКОРОСТЬ регена
        self.aggregator = StatsAggregationService(session)

    async def synchronize_state(self, char_id: int) -> dict[str, int]:
        """
        Главный метод.
        1. Читает старое состояние из Redis.
        2. Считает дельту времени.
        3. Начисляет реген.
        4. Сохраняет новое состояние обратно.
        Возвращает актуальные {hp, energy}.
        """
        # 1. Получаем текущие данные из Redis
        ac_data = await account_manager.get_account_data(char_id)
        if not ac_data:
            # Если данных нет вообще (первый вход), вернем нули
            return {"hp": 0, "energy": 0}

        # Безопасное извлечение с явным приведением типов
        last_update = float(ac_data.get("last_update", time.time()))
        current_hp = int(ac_data.get("hp_current", 0))
        current_energy = int(ac_data.get("energy_current", 0))

        # 2. Получаем Максимумы и Скорость регена через Агрегатор
        total_data = await self.aggregator.get_character_total_stats(char_id)
        modifiers: dict[str, Any] = total_data.get("modifiers", {})

        # Хелпер для извлечения значений из структуры агрегатора
        def get_val(key: str, default: float = 0.0) -> float:
            return float(modifiers.get(key, {}).get("total", default))

        hp_max = int(get_val("hp_max", 1.0))
        hp_regen = get_val("hp_regen", 0.0)  # Единиц в секунду
        energy_max = int(get_val("energy_max", 0.0))
        energy_regen = get_val("energy_regen", 0.0)

        # 3. Считаем Дельту
        now = time.time()
        time_delta = now - last_update

        # Защита от "путешественников во времени"
        if time_delta < 0:
            time_delta = 0

        # 4. Расчет восстановления
        hp_restored = int(time_delta * hp_regen)
        energy_restored = int(time_delta * energy_regen)

        new_hp = min(hp_max, current_hp + hp_restored)
        new_energy = min(energy_max, current_energy + energy_restored)

        # Логируем только значимые изменения
        if new_hp != current_hp or new_energy != current_energy:
            log.debug(
                f"Regen[{char_id}]: {time_delta:.1f}s passed. HP {current_hp}->{new_hp}, EN {current_energy}->{new_energy}"
            )

        # 5. Сохраняем актуальное состояние
        update_data: dict[str, Any] = {
            "hp_current": new_hp,
            "energy_current": new_energy,
            "last_update": now,
        }
        await account_manager.update_account_fields(char_id, update_data)

        return {"hp": new_hp, "energy": new_energy}
