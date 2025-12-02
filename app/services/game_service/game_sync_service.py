# app/services/game_service/game_sync_service.py

from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

# 🔥 НОВЫЕ ИМПОРТЫ для доступа к данным
from app.services.core_service.manager.account_manager import account_manager

# Импорт сервисов, которые будут оркестрироваться
from app.services.game_service.regen_service import RegenService
from app.services.game_service.stats_aggregation_service import StatsAggregationService


class GameSyncService:
    """
    Глобальный сервис-оркестратор для "ленивых" (JIT) и фоновых механик.

    Инкапсулирует вызовы всех сервисов, требующих синхронизации
    (регенерация, таймеры, AFK-прогресс), и предоставляет единую
    точку входа для хэндлеров.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализируется с сессией БД.
        """
        self.session = session
        log.debug("GameSyncService initialized.")

    async def synchronize_player_state(self, char_id: int) -> None:
        """
        Главный публичный метод. Вызывает все необходимые обновления
        для игрового состояния персонажа (в основном, регенерацию).
        """
        if not char_id:
            log.warning("SynchronizePlayerState skipped: char_id is None.")
            return

        log.info(f"GameSync: Starting full state synchronization for char_id={char_id}.")

        # 1. Lazy Regeneration (HP, Energy)
        regen_service = RegenService(self.session)
        await regen_service.synchronize_state(char_id)
        log.debug("GameSync: HP/Energy synchronized.")

        log.info(f"GameSync: State synchronization finished for char_id={char_id}.")

    # =========================================================================
    # 🔥 НОВЫЕ МЕТОДЫ: ДОСТУП К АКТУАЛЬНЫМ VITAL STATS
    # =========================================================================

    async def get_current_vitals(self, char_id: int) -> tuple[int, int]:
        """
        Возвращает текущие HP и Energy из кэша (Redis).
        (Считается, что перед вызовом уже была синхронизация/реген).
        """
        data = await account_manager.get_account_data(char_id)
        # ❗ ВАЖНО: Приводим к int, так как в кэше они могут храниться как str
        hp_cur = int(data.get("hp_current", 0)) if data else 0
        en_cur = int(data.get("energy_current", 0)) if data else 0
        log.debug(f"GameSync: Current vitals retrieved for {char_id}: HP={hp_cur}, EN={en_cur}")
        return hp_cur, en_cur

    async def get_max_vitals(self, char_id: int) -> tuple[int, int]:
        """
        Возвращает максимальные HP и Energy (Max Vitals), рассчитанные из статов.
        """
        aggregator = StatsAggregationService(self.session)
        total_data = await aggregator.get_character_total_stats(char_id)
        modifiers: dict[str, Any] = total_data.get("modifiers", {})

        # ❗ Извлекаем итоговые Max Vitals из агрегированных модификаторов
        hp_max = int(modifiers.get("hp_max", {}).get("total", 100))
        energy_max = int(modifiers.get("energy_max", {}).get("total", 100))

        log.debug(f"GameSync: Max vitals retrieved for {char_id}: HP={hp_max}, EN={energy_max}")
        return hp_max, energy_max

    async def get_quick_heal_check_func(self, char_id: int) -> Callable[[int], Awaitable[str | None]]:
        """
        Возвращает функцию-замыкание для Polling-анимации быстрого лечения.
        """
        regen_service = RegenService(self.session)

        # 1. Получаем Max Vitals для условия завершения
        hp_max, energy_max = await self.get_max_vitals(char_id)

        async def quick_recovery_tick(attempt: int) -> str | None:
            # 2. Вызываем JIT реген. Он сам обновит last_update и применит реген.
            updated_vitals = await regen_service.synchronize_state(char_id)

            # 3. Проверка на полное восстановление
            if updated_vitals["hp"] >= hp_max and updated_vitals["energy"] >= energy_max:
                return "Full"

            return None  # Продолжаем

        return quick_recovery_tick
