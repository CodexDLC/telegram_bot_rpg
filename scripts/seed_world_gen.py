import asyncio
import os
import random
import sys
from typing import Any, cast

from loguru import logger as log

# ==============================================================================
# 🔥 FIX: НАСТРОЙКИ ОКРУЖЕНИЯ ДОЛЖНЫ БЫТЬ ДО ИМПОРТОВ APP/DATABASE
# ==============================================================================
# 1. Определяем корень проекта (родитель папки scripts)
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(current_dir)

# 2. Переключаем рабочую директорию на корень (чтобы видеть папку /data)
os.chdir(PROJECT_ROOT)

# 3. Добавляем корень в sys.path (чтобы видеть пакет app)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
# ==============================================================================


@log.catch
async def seed_world_final():
    # --- Local Imports (after sys.path is configured) ---
    from app.resources.game_data.world_config import (
        HUB_CENTER,
        LOCATION_VARIANTS,
        SECTOR_ROWS,
        SECTOR_SIZE,
        STATIC_LOCATIONS,
        WORLD_HEIGHT,
        WORLD_WIDTH,
        ZONE_SIZE,
    )
    from app.services.game_service.world.content_gen_service import ContentGenerationService
    from app.services.game_service.world.threat_service import ThreatService
    from database.model_orm import Base
    from database.model_orm.world import WorldRegion
    from database.repositories import get_world_repo
    from database.session import async_engine, async_session_factory

    def get_sector_id_from_coords(x: int, y: int) -> str:
        col = (x // SECTOR_SIZE) + 1
        row_idx = y // SECTOR_SIZE
        row_idx = min(row_idx, len(SECTOR_ROWS) - 1)
        row_char = SECTOR_ROWS[row_idx]
        return f"{row_char}{col}"

    def _get_simple_line_path(x1, y1, x2, y2) -> list[tuple[int, int]]:
        """Строит прямую линию (ортогонально)."""
        path = []
        if x1 == x2:
            step_y = 1 if y2 > y1 else -1
            for y in range(y1, y2 + step_y, step_y):
                path.append((x1, y))
        elif y1 == y2:
            step_x = 1 if x2 > x1 else -1
            for x in range(x1, x2 + step_x, step_x):
                path.append((x, y1))
        return path

    log.info("🚀 World Seeding Pipeline V5.0 (Hub Cross Roads) Started")

    # 0. Init DB
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        repo = get_world_repo(session)
        content_service = ContentGenerationService(repo)

        # STAGE 1: МАКРО-СЕТКА
        log.info("🔹 Stage 1: Terrain Layout")
        region_cache = {}
        terrain_keys = list(LOCATION_VARIANTS.keys())
        for _row_idx, row_char in enumerate(SECTOR_ROWS):
            for col_idx in range(1, 8):
                sec_id = f"{row_char}{col_idx}"
                sector_map = {f"{zx}_{zy}": random.choice(terrain_keys) for zx in range(3) for zy in range(3)}
                region_obj = WorldRegion(id=sec_id, biome_id="dynamic", sector_map=sector_map, climate_tags=[])
                await repo.upsert_region(region_obj)
                region_cache[sec_id] = region_obj
        await session.flush()
        log.info("✅ Terrain layout generated.")

        # STAGE 2: МИКРО-СЕТКА
        log.info("🔹 Stage 2: Grid Injection")
        grid_tags_cache = {}
        for x in range(WORLD_WIDTH):
            for y in range(WORLD_HEIGHT):
                sec_id = get_sector_id_from_coords(x, y)
                region = region_cache.get(sec_id)
                if not region:
                    continue

                local_x, local_y = x % SECTOR_SIZE, y % SECTOR_SIZE
                sub_x, sub_y = local_x // ZONE_SIZE, local_y // ZONE_SIZE
                terrain_id = region.sector_map.get(f"{sub_x}_{sub_y}", "flat_wasteland")
                terrain_tags = LOCATION_VARIANTS.get(terrain_id, ["wasteland"])

                threat_val = ThreatService.calculate_threat(x, y)
                influence_tags = ThreatService.get_narrative_tags(x, y)
                final_tags = list(set(terrain_tags + influence_tags))
                grid_tags_cache[(x, y)] = final_tags

                flags_payload = {
                    "threat_val": round(threat_val, 3),
                    "threat_tier": ThreatService.get_tier_from_threat(threat_val),
                    "is_safe_zone": False,
                    "has_road": False,
                    "terrain_id": terrain_id,
                }
                content_payload = {"title": None, "description": None, "environment_tags": final_tags}
                await repo.create_or_update_node(
                    x=x, y=y, sector_id=sec_id, is_active=False, flags=flags_payload, content=content_payload
                )
            if x % 20 == 0:
                log.info(f"   ...column {x} processed")
        await session.commit()
        log.info("✅ Grid populated.")

        # STAGE 3: СТАТИКА
        log.info("🔹 Stage 3: Static Locations")
        for (sx, sy), data in STATIC_LOCATIONS.items():
            safe_content = cast(dict[str, Any], data["content"])
            await repo.create_or_update_node(
                x=sx,
                y=sy,
                sector_id=data["sector_id"],
                is_active=data["is_active"],
                flags=data["flags"],
                content=safe_content,
                service_key=data["service_object_key"],
            )
            if "environment_tags" in data["content"]:
                grid_tags_cache[(sx, sy)] = data["content"]["environment_tags"]
        await session.flush()

        # STAGE 4: ДОРОГИ
        log.info("🔹 Stage 4: Hub Cross Roads")
        hx, hy = HUB_CENTER["x"], HUB_CENTER["y"]
        target_points = [(hx, 45), (hx, 59), (45, hy), (59, hy)]
        llm_batch_queue = []
        for tx, ty in target_points:
            path = _get_simple_line_path(hx, hy, tx, ty)
            log.info(f"   Ray ({hx}:{hy}) -> ({tx}:{ty}) | Len: {len(path)}")
            for rx, ry in path:
                if (rx, ry) in STATIC_LOCATIONS:
                    continue
                await repo.update_flags(rx, ry, {"has_road": True}, activate_node=True)
                current_node = await repo.get_node(rx, ry)
                current_tags = []
                if current_node and current_node.content and isinstance(current_node.content, dict):
                    current_tags = current_node.content.get("environment_tags", [])
                if "road" not in current_tags:
                    current_tags.append("road")
                    await repo.update_content(rx, ry, {"environment_tags": current_tags})
                llm_batch_queue.append((rx, ry))
        await session.commit()
        log.info(f"✅ Rays activated. Queue: {len(llm_batch_queue)}")

        # STAGE 5: ГЕНЕРАЦИЯ
        if llm_batch_queue:
            log.info("🔹 Stage 5: AI Generation (Sequential Batches)")
            await content_service.generate_content_for_path(llm_batch_queue)
        await session.commit()

    log.info("🎉 World Seeding COMPLETED.")


if __name__ == "__main__":
    try:
        asyncio.run(seed_world_final())
    except (KeyboardInterrupt, SystemExit):
        log.info("Seeding interrupted manually.")
