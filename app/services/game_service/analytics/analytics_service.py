import asyncio
import csv
import os
from datetime import date

from loguru import logger as log


class AnalyticsService:
    """
    Сервис для сбора и записи аналитики боев.
    Пишет CSV асинхронно (в отдельном потоке), чтобы не блокировать бота.
    """

    def __init__(self):
        self.base_path = "data/analytics"
        os.makedirs(self.base_path, exist_ok=True)

        # Полный список полей для аналитики баланса
        # Мы используем плоскую структуру для 2 бойцов (1v1), так удобнее в Excel/Pandas
        self.fieldnames = [
            "timestamp",  # Время окончания боя (UNIX)
            "date_iso",  # Читаемая дата (YYYY-MM-DD)
            "session_id",  # ID сессии
            "winner_team",  # Победившая команда (blue/red/none)
            "duration_sec",  # Длительность в секундах
            "total_rounds",  # Количество раундов (обменов)
            # --- Участник 1 (Обычно Игрок / Blue) ---
            "p1_id",
            "p1_name",
            "p1_team",
            "p1_hp_left",
            "p1_energy_left",
            "p1_dmg_dealt",
            "p1_dmg_taken",
            "p1_healing",
            "p1_blocks",
            "p1_dodges",
            "p1_crits",
            # --- Участник 2 (Противник / Red) ---
            "p2_id",
            "p2_name",
            "p2_team",
            "p2_hp_left",
            "p2_energy_left",
            "p2_dmg_dealt",
            "p2_dmg_taken",
            "p2_healing",
            "p2_blocks",
            "p2_dodges",
            "p2_crits",
        ]

    async def log_combat_result(self, combat_data: dict) -> None:
        """
        Асинхронная обертка для записи.
        Принимает словарь с данными.
        """
        filename = f"{self.base_path}/combats_{date.today()}.csv"

        # Запускаем синхронную запись в отдельном потоке (ThreadPool)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_csv_sync, filename, combat_data)

    def _write_csv_sync(self, filename: str, data: dict) -> None:
        """
        Синхронная функция записи в файл. Выполняется в треде.
        """
        file_exists = os.path.isfile(filename)

        try:
            with open(filename, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)

                # Если файл новый — пишем заголовки
                if not file_exists:
                    writer.writeheader()

                # Фильтруем данные: берем только то, что есть в fieldnames
                # Если какого-то поля нет в data, пишем пустую строку или 0
                row = {k: data.get(k, "") for k in self.fieldnames}
                writer.writerow(row)

        except (OSError, csv.Error) as e:
            log.error(f"Ошибка записи аналитики в {filename}: {e}")


# Глобальный экземпляр
analytics_service = AnalyticsService()
