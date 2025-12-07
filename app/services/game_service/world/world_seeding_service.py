from loguru import logger as log
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.resources.game_data.world_config import SECTOR_ROWS, SECTOR_SIZE, STATIC_LOCATIONS, WORLD_HEIGHT, WORLD_WIDTH
from app.services.game_service.world.threat_service import ThreatService
from database.model_orm.world import WorldGrid, WorldSector


class WorldSeedingService:
    """
    Сервис инициализации мира (Seeding Layer).
    Отвечает за первичное заполнение базы данных (SQL) структурой мира.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_world_exists(self) -> bool:
        """
        Проверяет наличие мира в БД. Если пусто — запускает генерацию.
        Возвращает True, если генерация была произведена.
        """
        # 1. Проверка на наличие данных (Хеш/Маркер первого запуска)
        # Для простоты проверяем наличие хотя бы одной клетки
        stmt = select(func.count(WorldGrid.x))
        count = await self.session.scalar(stmt) or 0

        if count > 0:
            log.info(f"WorldSeeder | status=skipped reason='World already exists ({count} nodes)'")
            return False

        log.info("WorldSeeder | status=started reason='World grid is empty'")
        await self._generate_sectors()
        await self._generate_grid()
        return True

    async def _generate_sectors(self):
        """Генерация справочника секторов."""
        sectors_data = []
        for row_char in SECTOR_ROWS:
            for c_idx in range(1, 8):
                sec_id = f"{row_char}{c_idx}"
                # Упрощенная логика биомов
                biome = "hub" if sec_id == "D4" else "wasteland"

                if sec_id == "D4":
                    anchor_type = "HUB"
                elif sec_id in ["A4", "G4", "D1", "D7"]:
                    anchor_type = "ANCHOR_PRIME"
                else:
                    anchor_type = "WILD"

                sectors_data.append(WorldSector(id=sec_id, tier=1, biome_id=biome, anchor_type=anchor_type))

        # Используем merge для идемпотентности
        for sec in sectors_data:
            await self.session.merge(sec)
        await self.session.flush()
        log.debug("WorldSeeder | sectors_generated")

    async def _generate_grid(self):
        """Генерация матрицы 105x105."""
        grid_batch = []

        for y in range(WORLD_HEIGHT):
            for x in range(WORLD_WIDTH):
                col = (x // SECTOR_SIZE) + 1
                row_char = SECTOR_ROWS[y // SECTOR_SIZE]
                sec_id = f"{row_char}{col}"

                # --- ЛОГИКА КОНТЕНТА (STATIC vs PROCEDURAL) ---
                if (x, y) in STATIC_LOCATIONS:
                    # А. Статика (Хаб, Ворота)
                    static_data = STATIC_LOCATIONS[(x, y)]
                    is_active = static_data.get("is_active", True)
                    service_key = static_data.get("service_object_key")
                    flags = static_data.get("flags", {})
                    content = static_data.get("content")

                    threat_val = ThreatService.calculate_threat(x, y)
                    flags["threat_val"] = round(threat_val, 3)
                    flags["threat_tier"] = ThreatService.get_tier_from_threat(threat_val)

                else:
                    # Б. Процедурная Пустошь
                    is_active = False
                    service_key = None
                    content = None

                    threat_val = ThreatService.calculate_threat(x, y)
                    tier = ThreatService.get_tier_from_threat(threat_val)
                    narrative_tags = ThreatService.get_narrative_tags(x, y)

                    flags = {
                        "threat_val": round(threat_val, 3),
                        "threat_tier": tier,
                        "biome_tags": narrative_tags,
                        "generated": False,
                    }

                node = WorldGrid(
                    x=x,
                    y=y,
                    sector_id=sec_id,
                    is_active=is_active,
                    flags=flags,
                    content=content,
                    service_object_key=service_key,
                )
                grid_batch.append(node)

                if len(grid_batch) >= 2000:
                    self.session.add_all(grid_batch)
                    await self.session.flush()
                    grid_batch = []

        if grid_batch:
            self.session.add_all(grid_batch)
            await self.session.flush()  # Важно сделать flush перед commit в main

        log.debug("WorldSeeder | grid_generated")
