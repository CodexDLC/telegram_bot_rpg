import asyncio
import os
import random
import sys
from typing import Any, TypedDict, cast

from loguru import logger as log
from sqlalchemy import text

from apps.common.database.model_orm import Base
from apps.common.database.model_orm.world import WorldRegion, WorldZone
from apps.game_core.game_service.world.gen_utils.path_finder import PathFinder
from apps.game_core.game_service.world.zone_orchestrator import ZoneOrchestrator
from apps.game_core.resources.game_data.graf_data_world.start_vilage import (
    STATIC_LOCATIONS,
)
from apps.game_core.resources.game_data.graf_data_world.world_config import TerrainMeta

# ==============================================================================
# НАСТРОЙКИ ОКРУЖЕНИЯ
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(current_dir)
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

data_dir = os.path.join(PROJECT_ROOT, "data")
if not os.path.exists(data_dir):
    os.makedirs(data_dir, exist_ok=True)


# ==============================================================================
# ИМПОРТЫ
# ==============================================================================


class CellData(TypedDict):
    zone_id: str
    biome_id: str
    terrain_key: str
    tags: list[str]
    flags: dict[str, Any]
    content: dict[str, Any]
    services: list[str]


@log.catch
async def seed_world_final(mode: str = "test"):
    from apps.common.database.repositories import get_world_repo
    from apps.common.database.session import async_engine, async_session_factory
    from apps.game_core.game_service.world.content_gen_service import ContentGenerationService
    from apps.game_core.game_service.world.threat_service import ThreatService
    from apps.game_core.resources.game_data.graf_data_world.world_config import (
        ANCHORS,
        BIOME_DEFINITIONS,
        HUB_CENTER,
        REGION_ROWS,
        REGION_SIZE,
        ROAD_TAGS,
        WORLD_HEIGHT,
        WORLD_WIDTH,
        ZONE_SIZE,
    )

    def get_region_id(x: int, y: int) -> str:
        col = (x // REGION_SIZE) + 1
        row_idx = y // REGION_SIZE
        row_idx = min(row_idx, len(REGION_ROWS) - 1)
        row_char = REGION_ROWS[row_idx]
        return f"{row_char}{col}"

    def get_zone_id(x: int, y: int) -> str:
        reg_id = get_region_id(x, y)
        local_x = x % REGION_SIZE
        local_y = y % REGION_SIZE
        zone_x = local_x // ZONE_SIZE
        zone_y = local_y // ZONE_SIZE
        return f"{reg_id}_{zone_x}_{zone_y}"

    log.info(f"🚀 World Seeding Pipeline V17.0 (Lore & Tech Fix) Started. Mode: {mode}")

    if mode != "content_only":
        async with async_engine.begin() as conn:
            # Сброс базы для чистоты (новые биомы требуют пересоздания)
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        repo = get_world_repo(session)

        if mode != "content_only":
            # ======================================================================
            # STAGE 1: СТРУКТУРА (РЕГИОНЫ И ЗОНЫ)
            # ======================================================================
            log.info("🔹 Stage 1: Defining Regions & Zones")
            coord_to_zone: dict[tuple[int, int], str] = {}
            zone_biome_map: dict[str, str] = {}
            all_biomes = list(BIOME_DEFINITIONS.keys())

            for _, row_char in enumerate(REGION_ROWS):
                for col_idx in range(1, 8):
                    reg_id = f"{row_char}{col_idx}"
                    await repo.upsert_region(WorldRegion(id=reg_id, climate_tags=[]))

                    is_d4_region = reg_id == "D4"

                    for zx in range(3):
                        for zy in range(3):
                            zone_id = f"{reg_id}_{zx}_{zy}"

                            # === ЛОРНЫЙ ФИКС: ВЕСЬ D4 - ЭТО РУИНЫ ГОРОДА ===
                            biome = "city_ruins" if is_d4_region else random.choice(all_biomes)
                            # ===============================================

                            await repo.upsert_zone(WorldZone(id=zone_id, region_id=reg_id, biome_id=biome))
                            zone_biome_map[zone_id] = biome

            for x in range(WORLD_WIDTH):
                for y in range(WORLD_HEIGHT):
                    coord_to_zone[(x, y)] = get_zone_id(x, y)
            await session.flush()

            # ======================================================================
            # STAGE 2: МАТРИЦА
            # ======================================================================
            log.info("🔹 Stage 2: Generating World Matrix")
            world_matrix: dict[tuple[int, int], CellData] = {}

            for wx in range(WORLD_WIDTH):
                for wy in range(WORLD_HEIGHT):
                    z_id = coord_to_zone.get((wx, wy), "")
                    biome_id = zone_biome_map.get(z_id, "wasteland")
                    biome_config: dict[str, Any] = BIOME_DEFINITIONS.get(biome_id, {})

                    # Фон
                    backgrounds = [k for k, v in biome_config.items() if v.get("role") == "background"]
                    if not backgrounds:
                        backgrounds = ["flat"]
                    bg_weights = [biome_config.get(k, {}).get("spawn_weight", 10) for k in backgrounds]
                    try:
                        t_key = random.choices(backgrounds, weights=bg_weights, k=1)[0]
                    except IndexError:
                        t_key = "flat"

                    t_config_raw = biome_config.get(t_key) or {
                        "spawn_weight": 0,
                        "travel_cost": 1.0,
                        "is_passable": True,
                        "visual_tags": [],
                        "danger_mod": 1.0,
                        "role": "background",
                        "narrative_hint": "",
                    }
                    t_config = cast(TerrainMeta, t_config_raw)
                    threat_val = ThreatService.calculate_threat(wx, wy)

                    influence_tags = ThreatService.get_narrative_tags(wx, wy)
                    visual_tags = t_config.get("visual_tags", [])
                    final_tags = list(set(visual_tags + influence_tags))

                    cell: CellData = {
                        "zone_id": z_id,
                        "biome_id": biome_id,
                        "terrain_key": t_key,
                        "tags": final_tags,
                        "flags": {
                            "is_active": False,
                            "threat_val": round(threat_val, 3),
                            "threat_tier": ThreatService.get_tier_from_threat(threat_val),
                            "danger_mod": t_config.get("danger_mod", 1.0),
                            "is_safe_zone": (threat_val < 0.1),
                            "has_road": False,
                            "is_poi": False,
                            "is_gate": False,
                            "is_passable": t_config.get("is_passable", True),
                        },
                        "content": {"title": None, "description": None, "environment_tags": final_tags},
                        "services": [],
                    }

                    # --- СТЕНЫ ВНЕШНЕГО ПЕРИМЕТРА (ГРАНИЦА РЕГИОНА D4) ---
                    if z_id.startswith("D4"):
                        d4_min, d4_max = 45, 59
                        is_edge_x = wx in (d4_min, d4_max)
                        is_edge_y = wy in (d4_min, d4_max)

                        if is_edge_x or is_edge_y:
                            cell["terrain_key"] = "monolithic_wall"
                            cell["flags"]["is_passable"] = False
                            cell["tags"].append("outer_wall")

                    # --- СТАТИКА (ЦИТАДЕЛЬ) ---
                    if (wx, wy) in STATIC_LOCATIONS:
                        static_data = STATIC_LOCATIONS[(wx, wy)]
                        content = dict(static_data["content"]).copy()
                        if "environment_tags" not in content:
                            content["environment_tags"] = []
                        cell.update(
                            {
                                "terrain_key": "static_structure",
                                "tags": cast(list[str], content["environment_tags"]),
                                "flags": static_data["flags"],
                                "content": content,
                                "services": static_data.get("services", []),
                            }
                        )

                    world_matrix[(wx, wy)] = cell

            # ======================================================================
            # STAGE 3: ДОРОГИ И ВОРОТА
            # ======================================================================
            log.info("🔹 Stage 3: Building Road Network")
            graph_nodes = [(HUB_CENTER["x"], HUB_CENTER["y"])]
            graph_nodes.extend((anchor["x"], anchor["y"]) for anchor in ANCHORS)
            for (x, y), cell in world_matrix.items():
                if cell["flags"].get("is_gate") or cell["flags"].get("is_poi"):
                    graph_nodes.append((x, y))
            graph_nodes = list(set(graph_nodes))

            path_finder = PathFinder(zone_biome_map, coord_to_zone)
            road_cells_set = path_finder.build_road_network(graph_nodes)

            log.info(f"   ...Processing {len(road_cells_set)} road cells...")
            for rx, ry in road_cells_set:
                if (rx, ry) in world_matrix and not world_matrix[(rx, ry)]["services"]:
                    cell = world_matrix[(rx, ry)]
                    cell["flags"]["has_road"] = True

                    # === ТЕХНИЧЕСКИЙ ФИКС: ВОРОТА ВМЕСТО СНОСА СТЕН ===
                    if cell["terrain_key"] == "monolithic_wall":
                        cell["terrain_key"] = "city_gate_outer"
                        cell["flags"]["is_gate"] = True
                        cell["flags"]["is_poi"] = True
                        cell["flags"]["is_passable"] = True
                        cell["tags"].append("massive_gate")
                        cell["content"]["environment_tags"].append("massive_gate")
                        continue  # Не меняем на обычную дорогу
                    # ==================================================

                    biome_conf = BIOME_DEFINITIONS.get(cell["biome_id"], {})
                    road_key = "road"
                    found = False
                    for k in biome_conf:
                        if k in ROAD_TAGS:
                            road_key = k
                            found = True
                            break
                    if not found:
                        for k in biome_conf:
                            if "road" in k or "path" in k:
                                road_key = k
                                found = True
                                break

                    # Fallback для City Ruins (если конфиг не нашел)
                    if not found and cell["biome_id"] == "city_ruins":
                        road_key = "ruin_road_main"

                    if road_key in biome_conf:
                        road_conf = biome_conf[road_key]
                        road_tags = road_conf.get("visual_tags", ["road"])
                        cell["tags"].extend(road_tags)
                        cell["content"]["environment_tags"].extend(road_tags)
                        if not cell["flags"].get("is_poi") and not cell["flags"].get("is_gate"):
                            cell["terrain_key"] = road_key

            # ======================================================================
            # STAGE 4: ЗАПИСЬ В БД
            # ======================================================================
            log.info("🔹 Stage 4: Dumping Matrix to DB")
            for (x, y), cell in world_matrix.items():
                cell["content"]["environment_tags"] = list(set(cell["content"]["environment_tags"]))
                cell["tags"] = list(set(cell["tags"]))
                await repo.create_or_update_node(
                    x=x,
                    y=y,
                    zone_id=cell["zone_id"],
                    terrain_type=cell["terrain_key"],
                    is_active=cell["flags"].get("is_active", False),
                    flags=cell["flags"],
                    content=cell["content"],
                    services=cell["services"],
                )
            await session.commit()
            log.info("✅ World Matrix Saved to DB.")
        else:
            log.info("⏩ Skipping Stages 1-4 (Content Only Mode)")

        # ======================================================================
        # STAGE 5: АКТИВАЦИЯ И ГЕНЕРАЦИЯ (С SQL ФИКСОМ)
        # ======================================================================
        log.info("🔹 Stage 5: Activating Region D4")
        content_service = ContentGenerationService(repo)
        orchestrator = ZoneOrchestrator(repo, content_service)

        # === ФУНКЦИЯ ДЛЯ ПРАВИЛЬНОЙ АКТИВАЦИИ ===
        async def force_activate_cell(sess, cx, cy):
            # Обновляем напрямую через SQL, чтобы обойти баг ORM/Repo
            await sess.execute(
                text(
                    """
                UPDATE world_grid 
                SET is_active = 1, 
                    flags = json_patch(flags, '{"is_active": true}')
                WHERE x = :x AND y = :y
            """
                ),
                {"x": cx, "y": cy},
            )

        # ==========================================

        # 1. Активируем ХАБ
        hub_center_x, hub_center_y = 52, 52
        log.info("   Activating STATIC CITADEL zone...")
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                await force_activate_cell(session, hub_center_x + dx, hub_center_y + dy)

        # 2. Обрабатываем соседей
        region_d4_centers = []
        start_x = 45
        start_y = 45
        for zx in range(3):
            for zy in range(3):
                cx = start_x + zx * 5 + 2
                cy = start_y + zy * 5 + 2
                if cx == 52 and cy == 52:
                    continue
                region_d4_centers.append((cx, cy))

        log.info(f"   Processing {len(region_d4_centers)} procedural zones...")

        for i, (cx, cy) in enumerate(region_d4_centers, 1):
            zone_id = get_zone_id(cx, cy)
            log.info(f"   [{i}] Generating & Activating zone {zone_id}...")

            # А. Генерируем описание (ИИ)
            await orchestrator.generate_chunk(cx, cy)

            # Б. Включаем рубильник активности для всей зоны
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    await force_activate_cell(session, cx + dx, cy + dy)

            log.info(f"       -> Zone {zone_id} is now ACTIVE.")

            if mode == "test":
                log.warning("   TEST MODE: Stopping after first procedural zone.")
                break

        await session.commit()
        log.info("🎉 World Seeding COMPLETED.")


if __name__ == "__main__":
    print("Выберите режим запуска:")
    print("1. Тестовый режим (генерация мира + 1 активная зона D4)")
    print("2. Полный режим (генерация мира + все 8 активных зон D4)")
    print("3. Content Only (только Stage 5: пере-активация)")
    choice = input("Введите 1, 2 или 3: ")
    run_mode = "test" if choice == "1" else "content_only" if choice == "3" else "full"
    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(seed_world_final(mode=run_mode))
    except (KeyboardInterrupt, SystemExit):
        log.info("Seeding interrupted.")
