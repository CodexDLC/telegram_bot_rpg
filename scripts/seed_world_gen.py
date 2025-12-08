import asyncio
import os
import random
import sys
from typing import Any, cast

from loguru import logger as log

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

# ==============================================================================
# 🔥 FIX PATHS: Настройка окружения перед импортами
# ==============================================================================
# 1. Определяем корень проекта (родитель папки scripts)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Переключаем рабочую директорию на корень (чтобы видеть папку /data)
os.chdir(PROJECT_ROOT)

# 3. Добавляем корень в sys.path (чтобы видеть пакет app)
sys.path.append(PROJECT_ROOT)
# ==============================================================================


def get_sector_id_from_coords(x: int, y: int) -> str:
    col = (x // SECTOR_SIZE) + 1
    row_idx = y // SECTOR_SIZE
    row_idx = min(row_idx, len(SECTOR_ROWS) - 1)
    row_char = SECTOR_ROWS[row_idx]
    return f"{row_char}{col}"


# 🔥 FIX 1: Декоратор для перехвата крашей
@log.catch
async def seed_world_final():
    log.info("🚀 World Seeding Pipeline V4.0 (Influence-Based + Linter Fix) Started")

    # 0. Инициализация таблиц
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        repo = get_world_repo(session)
        content_service = ContentGenerationService(repo)

        # ======================================================================
        # STAGE 1: МАКРО-СЕТКА (REGIONS 7x7)
        # Чистая генерация ландшафта из LOCATION_VARIANTS.
        # ======================================================================
        log.info("🔹 Stage 1: Terrain Layout")

        region_cache = {}
        # Берем ключи доступных типов местности (flat_wasteland, rocky_hills...)
        terrain_keys = list(LOCATION_VARIANTS.keys())

        for _row_idx, row_char in enumerate(SECTOR_ROWS):
            for col_idx in range(1, 8):
                sec_id = f"{row_char}{col_idx}"

                # Генерируем карту под-зон (3x3)
                sector_map = {}
                for zx in range(3):
                    for zy in range(3):
                        # Случайный выбор ландшафта для квадрата 5x5
                        chosen_terrain = random.choice(terrain_keys)
                        sector_map[f"{zx}_{zy}"] = chosen_terrain

                region_obj = WorldRegion(
                    id=sec_id,
                    biome_id="dynamic",  # Никаких wasteland/ice палитр, всё динамическое
                    sector_map=sector_map,
                    climate_tags=[],
                )
                await repo.upsert_region(region_obj)
                region_cache[sec_id] = region_obj

        await session.flush()
        log.info("✅ Terrain layout generated.")

        # ======================================================================
        # STAGE 2: МИКРО-СЕТКА (GRID 105x105)
        # Смешивание Terrain + Influence Tags.
        # ======================================================================
        log.info("🔹 Stage 2: Grid Injection (Terrain + Influence)")

        grid_tags_cache = {}

        for x in range(WORLD_WIDTH):
            for y in range(WORLD_HEIGHT):
                sec_id = get_sector_id_from_coords(x, y)
                region = region_cache.get(sec_id)
                if not region:
                    continue

                # 1. Ландшафт (из карты региона)
                local_x = x % SECTOR_SIZE
                local_y = y % SECTOR_SIZE
                sub_x = local_x // ZONE_SIZE
                sub_y = local_y // ZONE_SIZE

                terrain_id = region.sector_map.get(f"{sub_x}_{sub_y}", "flat_wasteland")
                terrain_tags = LOCATION_VARIANTS.get(terrain_id, ["wasteland"])

                # 2. Влияние (из ThreatService -> INFLUENCE_TAGS)
                threat_val = ThreatService.calculate_threat(x, y)
                influence_tags = ThreatService.get_narrative_tags(x, y)

                # 3. Геометрия
                geo_tags = []
                inner_x = local_x % ZONE_SIZE
                inner_y = local_y % ZONE_SIZE
                if inner_x == 2 and inner_y == 2:
                    geo_tags.append("zone_center")

                # 4. Финальный микс
                final_tags = list(set(terrain_tags + influence_tags + geo_tags))
                grid_tags_cache[(x, y)] = final_tags

                content_payload = {"title": None, "description": None, "environment_tags": final_tags}

                flags_payload = {
                    "threat_val": round(threat_val, 3),
                    "threat_tier": ThreatService.get_tier_from_threat(threat_val),
                    "is_safe_zone": False,
                    "has_road": False,
                    "terrain_id": terrain_id,
                }

                await repo.create_or_update_node(
                    x=x, y=y, sector_id=sec_id, is_active=False, flags=flags_payload, content=content_payload
                )

            if x % 20 == 0:
                log.info(f"   ...column {x} processed")

        await session.commit()
        log.info("✅ Grid populated.")

        # ======================================================================
        # STAGE 3: СТАТИКА (STATIC OVERLAY)
        # ======================================================================
        log.info("🔹 Stage 3: Static Locations")
        for (sx, sy), data in STATIC_LOCATIONS.items():
            # Приведение типов для mypy/ruff
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
            # Обновляем кэш тегов для дорог
            if "environment_tags" in data["content"]:
                grid_tags_cache[(sx, sy)] = data["content"]["environment_tags"]  # type: ignore

        await session.flush()

        # ======================================================================
        # STAGE 4: ДОРОГИ (ROADS)
        # ======================================================================
        log.info("🔹 Stage 4: Roads & Context Assembly")

        hx, hy = HUB_CENTER["x"], HUB_CENTER["y"]
        offsets = [(-15, -15), (0, -15), (15, -15), (-15, 0), (15, 0), (-15, 15), (0, 15), (15, 15)]

        llm_batch_queue = []

        for dx, dy in offsets:
            target_x, target_y = hx + dx, hy + dy
            path = _get_simple_line_path(hx, hy, target_x, target_y)
            log.info(f"   Road to neighbor ({target_x}:{target_y})...")

            for rx, ry in path:
                if (rx, ry) in STATIC_LOCATIONS:
                    continue

                await repo.update_flags(rx, ry, {"has_road": True}, activate_node=True)

                base_tags = grid_tags_cache.get((rx, ry), [])
                if "road" not in base_tags:
                    base_tags.append("road")

                new_content = {"title": None, "description": None, "environment_tags": base_tags}
                await repo.update_content(rx, ry, new_content)

                llm_batch_queue.append((rx, ry))

        await session.commit()
        log.info(f"✅ Roads activated. Queue size: {len(llm_batch_queue)}")

        # ======================================================================
        # STAGE 5: ГЕНЕРАЦИЯ (LLM EXECUTION)
        # ======================================================================
        if llm_batch_queue:
            log.info("🔹 Stage 5: AI Generation (The Travelogue)")
            await content_service.generate_content_for_path(llm_batch_queue)

        await session.commit()

    log.info("🎉 World Seeding COMPLETED.")


def _get_simple_line_path(x1, y1, x2, y2) -> list[tuple[int, int]]:
    path = []
    step_x = 1 if x2 > x1 else -1
    for x in range(x1, x2, step_x):
        path.append((x, y1))
    step_y = 1 if y2 > y1 else -1
    for y in range(y1, y2, step_y):
        path.append((x2, y))
    path.append((x2, y2))
    return path


# 🔥 FIX 2: Безопасный запуск без слепого except
if __name__ == "__main__":
    try:
        asyncio.run(seed_world_final())
    except (KeyboardInterrupt, SystemExit):
        log.info("Seeding interrupted manually.")
