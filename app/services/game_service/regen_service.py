import time
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.core_service.manager.account_manager import account_manager
from app.services.game_service.stats_aggregation_service import StatsAggregationService

BASE_REGEN_TIME_SEC = 300.0
ENDURANCE_REGEN_BONUS = 0.1


class RegenService:
    """
    Сервис "Ленивого восстановления" (Lazy Regeneration).

    Вычисляет восстановление HP и Energy персонажа на основе прошедшего времени
    с момента последнего обновления.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует RegenService.

        Args:
            session: Асинхронная сессия базы данных.
        """
        self.session = session
        self.aggregator = StatsAggregationService(session)
        log.debug("RegenService | status=initialized")

    async def synchronize_state(self, char_id: int) -> dict[str, int]:
        """
        Синхронизирует состояние HP и Energy персонажа, применяя регенерацию.

        1. Получает текущие данные персонажа из Redis.
        2. Вычисляет прошедшее время с последнего обновления.
        3. Рассчитывает количество восстановленных HP и Energy.
        4. Обновляет данные персонажа в Redis.

        Args:
            char_id: Уникальный идентификатор персонажа.

        Returns:
            Словарь с актуальными значениями "hp" и "energy" после регенерации.
        """
        ac_data = await account_manager.get_account_data(char_id)
        if not ac_data:
            log.warning(f"RegenService | status=skipped reason='Account data not found' char_id={char_id}")
            return {"hp": 0, "energy": 0}

        last_update = float(ac_data.get("last_update", time.time()))
        current_hp = int(ac_data.get("hp_current", 0))
        current_energy = int(ac_data.get("energy_current", 0))

        total_data = await self.aggregator.get_character_total_stats(char_id)
        modifiers: dict[str, Any] = total_data.get("modifiers", {})
        stats: dict[str, Any] = total_data.get("stats", {})

        def get_val(key: str, default: float = 0.0) -> float:
            return float(modifiers.get(key, {}).get("total", default))

        hp_max = get_val("hp_max", 1.0)
        base_regen_rate = hp_max / BASE_REGEN_TIME_SEC
        endurance_info = stats.get("endurance", {}).get("total", 0.0)
        endurance_val = float(endurance_info)
        bonus_regen_rate = endurance_val * ENDURANCE_REGEN_BONUS
        total_hp_regen = base_regen_rate + bonus_regen_rate

        energy_max = int(get_val("energy_max", 0.0))
        energy_regen = get_val("energy_regen", 0.0)

        now = time.time()
        time_delta = now - last_update
        if time_delta < 0:
            time_delta = 0

        hp_restored = int(time_delta * total_hp_regen)
        energy_restored = int(time_delta * energy_regen)

        new_hp = min(hp_max, current_hp + hp_restored)
        new_energy = min(energy_max, current_energy + energy_restored)

        if new_hp != current_hp or new_energy != current_energy:
            log.debug(
                f"RegenService | char_id={char_id} time_delta={time_delta:.1f}s "
                f"hp_old={current_hp} hp_new={new_hp} "
                f"energy_old={current_energy} energy_new={new_energy}"
            )

        update_data: dict[str, Any] = {
            "hp_current": int(new_hp),
            "energy_current": new_energy,
            "last_update": now,
        }
        await account_manager.update_account_fields(char_id, update_data)

        return {"hp": int(new_hp), "energy": new_energy}
