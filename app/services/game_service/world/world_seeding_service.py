from typing import Any, cast

from loguru import logger as log

from app.resources.game_data.world_config import SECTOR_ROWS, SECTOR_SIZE, STATIC_LOCATIONS, WORLD_HEIGHT, WORLD_WIDTH
from app.services.game_service.world.threat_service import ThreatService
from database.db_contract.i_world_repo import IWorldRepo
from database.model_orm.world import WorldRegion


class WorldSeedingService:
    """
    Сервис инициализации мира (Seeding Layer).
    Отвечает за первичное заполнение базы данных (SQL) структурой мира.
    Работает через репозиторий, не зависит от ORM напрямую.
    """

    def __init__(self, repo: IWorldRepo):
        self.repo = repo

    async def ensure_world_exists(self) -> bool:
        """
        Проверяет наличие мира в БД. Если пусто — запускает генерацию.
        Возвращает True, если генерация была произведена.
        """
        # Проверяем через репозиторий
        active_nodes = await self.repo.get_active_nodes()
        if active_nodes:
            log.info(f"WorldSeeder | status=skipped reason='World already exists ({len(active_nodes)} nodes)'")
            return False

        log.info("WorldSeeder | status=started reason='World grid is empty'")
        await self._generate_sectors()
        await self._generate_grid()
        return True

    async def _generate_sectors(self):
        """Генерация справочника регионов (бывшие сектора)."""
        for row_char in SECTOR_ROWS:
            for c_idx in range(1, 8):
                sec_id = f"{row_char}{c_idx}"
                biome = "hub" if sec_id == "D4" else "wasteland"

                region_obj = WorldRegion(
                    id=sec_id,
                    biome_id=biome,
                    climate_tags=[],  # Заполняется на следующем этапе
                    sector_map={},  # Заполняется на следующем этапе
                )
                await self.repo.upsert_region(region_obj)
        log.debug("WorldSeeder | regions_generated")

    async def _generate_grid(self):
        """Генерация матрицы 105x105."""
        for y in range(WORLD_HEIGHT):
            for x in range(WORLD_WIDTH):
                col = (x // SECTOR_SIZE) + 1
                row_char = SECTOR_ROWS[y // SECTOR_SIZE]
                sec_id = f"{row_char}{col}"

                if (x, y) in STATIC_LOCATIONS:
                    static_data = STATIC_LOCATIONS[(x, y)]
                    is_active = static_data.get("is_active", True)
                    service_key = static_data.get("service_object_key")
                    flags = static_data.get("flags", {}).copy()
                    content = cast(dict[str, Any], static_data.get("content"))

                    threat_val = ThreatService.calculate_threat(x, y)
                    flags["threat_val"] = round(threat_val, 3)
                    flags["threat_tier"] = ThreatService.get_tier_from_threat(threat_val)
                else:
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

                await self.repo.create_or_update_node(
                    x=x,
                    y=y,
                    sector_id=sec_id,
                    is_active=is_active,
                    flags=flags,
                    content=content,
                    service_key=service_key,
                )

        log.debug("WorldSeeder | grid_generated")
