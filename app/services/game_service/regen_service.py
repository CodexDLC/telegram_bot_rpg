import time
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.core_service.manager.account_manager import account_manager
from app.services.game_service.stats_aggregation_service import StatsAggregationService

# 🔥 НОВЫЕ КОНСТАНТЫ
BASE_REGEN_TIME_SEC = 300.0  # Цель: полное восстановление за 5 минут (можно легко изменить)
ENDURANCE_REGEN_BONUS = 0.1  # Бонусный множитель от Выносливости (по запросу)


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
        stats: dict[str, Any] = total_data.get("stats", {})

        # Хелпер для извлечения значений из структуры агрегатора
        def get_val(key: str, default: float = 0.0) -> float:
            return float(modifiers.get(key, {}).get("total", default))

        # --- 3. Расчет HP Regen Rate (Новая формула) ---
        hp_max = get_val("hp_max", 1.0)

        # 3.1. Базовый реген (Процентный, для восстановления Max HP за BASE_REGEN_TIME_SEC)
        base_regen_rate = hp_max / BASE_REGEN_TIME_SEC

        # 3.2. Бонусный реген (от Endurance - используем агрегированный стат)
        # Нам нужно значение Endurance из 'stats' (базовые статы находятся там)
        endurance_info = stats.get("endurance", {}).get("total", 0.0)
        endurance_val = float(endurance_info)
        bonus_regen_rate = endurance_val * ENDURANCE_REGEN_BONUS

        # 3.3. Общая скорость регенерации HP
        total_hp_regen = base_regen_rate + bonus_regen_rate

        # --- 4. Расчет Energy Regen Rate (Старая формула) ---
        energy_max = int(get_val("energy_max", 0.0))
        energy_regen = get_val("energy_regen", 0.0)  # Берется из MODIFIER_RULES (зависит от Men)

        # 5. Считаем Дельту
        now = time.time()
        time_delta = now - last_update

        # Защита от "путешественников во времени"
        if time_delta < 0:
            time_delta = 0

        # 6. Расчет восстановления
        hp_restored = int(time_delta * total_hp_regen)
        energy_restored = int(time_delta * energy_regen)

        new_hp = min(hp_max, current_hp + hp_restored)
        new_energy = min(energy_max, current_energy + energy_restored)

        # Логируем только значимые изменения
        if new_hp != current_hp or new_energy != current_energy:
            log.debug(
                f"Regen[{char_id}]: {time_delta:.1f}s passed. HP {current_hp}->{new_hp}, EN {current_energy}->{new_energy}"
            )

        # 7. Сохраняем актуальное состояние
        update_data: dict[str, Any] = {
            "hp_current": int(new_hp),
            "energy_current": new_energy,
            "last_update": now,
        }
        await account_manager.update_account_fields(char_id, update_data)

        return {"hp": int(new_hp), "energy": new_energy}
