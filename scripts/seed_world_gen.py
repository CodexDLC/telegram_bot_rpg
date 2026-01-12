# scripts/seed_world_gen.py
import asyncio
import math
import os
import random
import sys
from typing import cast

from loguru import logger as log

# --- Адаптация под структуру проекта ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from apps.common.database.model_orm.base import Base  # noqa: E402
from apps.common.database.model_orm.world import WorldRegion, WorldZone  # noqa: E402
from apps.common.database.repositories.ORM.world_repo import WorldRepoORM  # noqa: E402
from apps.common.database.session import async_engine, async_session_factory  # noqa: E402
from apps.game_core.resources.graf_data_world.start_vilage import STATIC_LOCATIONS  # noqa: E402
from apps.game_core.resources.graf_data_world.world_config import (  # noqa: E402
    BIOME_DEFINITIONS,
    HUB_CENTER,
    REGION_ROWS,
    REGION_SIZE,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    ZONE_SIZE,
    TerrainMeta,
)
from apps.game_core.system.factories.monster.clan_factory import ClanFactory  # noqa: E402
from apps.game_core.system.factories.world.content_gen_service import ContentGenerationService  # noqa: E402
from apps.game_core.system.factories.world.gen_utils.path_finder import PathFinder  # noqa: E402
from apps.game_core.system.factories.world.threat_service import ThreatService  # noqa: E402
from apps.game_core.system.factories.world.zone_orchestrator import ZoneOrchestrator  # noqa: E402


class WorldGenerator:
    def __init__(self, session):
        self.session = session
        self.world_repo = WorldRepoORM(session)
        self.clan_factory = ClanFactory(session)
        self.content_service = ContentGenerationService(self.world_repo)
        self.zone_orchestrator = ZoneOrchestrator(session, self.world_repo, self.content_service)
        self.regional_pois = []
        log.debug("WorldGeneratorInit")

    async def run(self, mode: str = "test") -> None:
        log.info(f"WorldGen | event=start mode={mode}")
        if mode != "content_only":
            log.info("WorldGen | step=1_create_structure")
            await self._create_regions_and_zones()
            log.info("WorldGen | step=2_generate_matrix_ram")
            world_matrix = self._generate_world_matrix()
            world_matrix = self._build_world_skeleton(world_matrix)
            log.info(f"WorldGen | step=3_bulk_save items={len(world_matrix)}")
            await self._save_matrix_bulk(world_matrix)
            await self.session.commit()
            log.info("WorldGen | event=structure_committed")
        log.info("WorldGen | step=4_spawn_content")
        await self._spawn_content(mode)
        await self.session.commit()
        log.info("WorldGen | event=complete")

    async def _create_regions_and_zones(self) -> None:
        for row_char in REGION_ROWS:
            for col_idx in range(1, 8):
                reg_id = f"{row_char}{col_idx}"
                await self.world_repo.upsert_region(WorldRegion(id=reg_id, climate_tags=[]))
                for zx in range(3):
                    for zy in range(3):
                        zone_id = f"{reg_id}_{zx}_{zy}"
                        reg_row_idx = REGION_ROWS.index(row_char)
                        center_x = (col_idx - 1) * REGION_SIZE + zx * ZONE_SIZE + ZONE_SIZE // 2
                        center_y = reg_row_idx * REGION_SIZE + zy * ZONE_SIZE + ZONE_SIZE // 2
                        flags = {}
                        if reg_id == "D4":
                            if zx == 1 and zy == 1:
                                biome_id = "hub_district"
                                tier = 0
                                flags = {"is_safe_zone": True, "is_passable": True}
                            else:
                                biome_id = "city_ruins"
                                tier = 0
                                flags = {"is_safe_zone": False, "is_passable": True}
                        else:
                            biome_id = self._get_biome_noise(center_x, center_y)
                            dist = math.sqrt((center_x - 52) ** 2 + (center_y - 52) ** 2)
                            tier = min(7, int(dist / 15) + 1)
                        await self.world_repo.upsert_zone(
                            WorldZone(id=zone_id, region_id=reg_id, biome_id=biome_id, tier=tier, flags=flags)
                        )
        await self.session.flush()

    def _get_biome_noise(self, x: int, y: int) -> str:
        natural_biomes = ["forest", "swamp", "mountains", "wasteland", "canyon", "jungle", "badlands", "grassland"]
        scale = 0.12
        val = math.sin(x * scale) + math.cos(y * scale * 0.8) + math.sin((x + y) * 0.05)
        normalized = (val + 3) / 6
        idx = int(normalized * len(natural_biomes))
        idx = max(0, min(idx, len(natural_biomes) - 1))
        return natural_biomes[idx]

    def _generate_world_matrix(self) -> dict:
        matrix = {}
        for wx in range(WORLD_WIDTH):
            for wy in range(WORLD_HEIGHT):
                col = (wx // REGION_SIZE) + 1
                row_idx = min(wy // REGION_SIZE, len(REGION_ROWS) - 1)
                row_char = REGION_ROWS[row_idx]
                reg_id = f"{row_char}{col}"
                local_x, local_y = wx % REGION_SIZE, wy % REGION_SIZE
                zone_x, zone_y = local_x // ZONE_SIZE, local_y // ZONE_SIZE
                zone_id = f"{reg_id}_{zone_x}_{zone_y}"
                biome_id = "city_ruins" if reg_id == "D4" else self._get_biome_noise(wx, wy)
                biome_config = BIOME_DEFINITIONS.get(biome_id, {})
                t_key = "flat"
                if biome_config:
                    population, weights = [], []
                    for key, data in biome_config.items():
                        if data.get("role") == "background" and data.get("spawn_weight", 0) > 0:
                            population.append(key)
                            weights.append(data["spawn_weight"])
                    if population:
                        t_key = random.choices(population, weights=weights, k=1)[0]
                    else:
                        t_key = next(iter(biome_config.keys()), "flat")

                terrain_meta: TerrainMeta = cast(TerrainMeta, biome_config.get(t_key, {}))
                env_tags = terrain_meta.get("visual_tags", []) + [biome_id]

                # --- ИЗМЕНЕНО: Только Threat Tier, без автоматического Safe Zone ---
                threat_val = ThreatService.calculate_threat(wx, wy)
                threat_tier = ThreatService.get_tier_from_threat(threat_val)

                # is_safe_zone здесь НЕ ставим, он придет из статики или зоны
                flags = {
                    "is_passable": terrain_meta.get("is_passable", True),
                    "threat_tier": threat_tier,
                }

                matrix[(wx, wy)] = {
                    "x": wx,
                    "y": wy,
                    "zone_id": zone_id,
                    "terrain_type": t_key,
                    "tags": list(set(env_tags)),
                    "flags": flags,
                    "content": {"title": t_key, "description": "", "environment_tags": list(set(env_tags))},
                    "services": [],
                }
        return matrix

    def _build_world_skeleton(self, matrix: dict) -> dict:
        # 1. Статика (Хаб) - здесь проставляется is_safe_zone для конкретных клеток
        for (wx, wy), static_data in STATIC_LOCATIONS.items():
            if (wx, wy) in matrix:
                cell = matrix[(wx, wy)]
                cell["terrain_type"] = "static_structure"
                # Обновляем флаги (включая is_safe_zone из статики)
                cell["flags"].update(static_data["flags"])
                cell["content"] = dict(static_data["content"])
                cell["services"] = static_data.get("services", [])
                if "environment_tags" in cell["content"]:
                    cell["tags"] = cell["content"]["environment_tags"]

        # ... (остальной код без изменений) ...

        d4_min, d4_max = 45, 59
        gates = []
        for x in range(d4_min, d4_max + 1):
            for y in range(d4_min, d4_max + 1):
                if x in (d4_min, d4_max) or y in (d4_min, d4_max):
                    mid = (d4_min + d4_max) // 2
                    if x == mid or y == mid:
                        matrix[(x, y)]["terrain_type"] = "city_gate_outer"
                        matrix[(x, y)]["tags"].append("gate")
                        matrix[(x, y)]["flags"]["is_passable"] = True
                        gates.append((x, y))
                    else:
                        matrix[(x, y)]["terrain_type"] = "monolithic_wall"
                        matrix[(x, y)]["tags"].append("wall")
                        matrix[(x, y)]["flags"]["is_passable"] = False

        self.regional_pois = []
        for row_char in REGION_ROWS:
            for col_idx in range(1, 8):
                reg_id = f"{row_char}{col_idx}"
                if reg_id == "D4":
                    continue
                cx = (col_idx - 1) * REGION_SIZE + REGION_SIZE // 2
                cy = REGION_ROWS.index(row_char) * REGION_SIZE + REGION_SIZE // 2
                if (cx, cy) in matrix:
                    matrix[(cx, cy)]["terrain_type"] = "ancient_ruin_poi"
                    matrix[(cx, cy)]["tags"].append("poi")
                    matrix[(cx, cy)]["flags"]["is_poi"] = True
                    self.regional_pois.append((cx, cy))

        matrix = self._generate_roads_graph(matrix, gates)
        return matrix

    def _calculate_costs_for_pathfinding(self, matrix: dict) -> None:
        terrain_props_cache = {}
        for _biome_key, terrains in BIOME_DEFINITIONS.items():
            for t_key, t_data in terrains.items():
                terrain_props_cache[t_key] = {
                    "cost": t_data.get("travel_cost", 1.0),
                    "is_passable": t_data.get("is_passable", True),
                }
        terrain_props_cache["static_structure"] = {"cost": 999.0, "is_passable": False}
        for cell in matrix.values():
            props = terrain_props_cache.get(cell["terrain_type"])
            base_cost = props["cost"] if props else 1.0
            conf_passable = props["is_passable"] if props else True
            if not conf_passable or not cell["flags"].get("is_passable", True) or base_cost <= 0.01:
                final_cost = 999.0
            else:
                final_cost = base_cost
            if "road" in cell["tags"]:
                final_cost = min(final_cost, 0.5)
            cell["flags"]["travel_cost"] = final_cost

    def _generate_roads_graph(self, matrix: dict, gates: list) -> dict:
        self._calculate_costs_for_pathfinding(matrix)
        path_finder = PathFinder(matrix)
        road_cells = set()
        hub_pt = (HUB_CENTER["x"], HUB_CENTER["y"])
        for gate in gates:
            path = path_finder.get_path(hub_pt, gate)
            if path:
                road_cells.update(path)
        for gate in gates:
            if not self.regional_pois:
                continue
            closest_poi = min(self.regional_pois, key=lambda p: abs(p[0] - gate[0]) + abs(p[1] - gate[1]))
            path = path_finder.get_path(gate, closest_poi)
            if path:
                road_cells.update(path)

        for rx, ry in road_cells:
            if (rx, ry) not in matrix:
                continue
            cell = matrix[(rx, ry)]
            if cell["terrain_type"] in ["static_structure", "monolithic_wall"]:
                continue
            cell["flags"]["is_passable"] = True
            cell["flags"]["has_road"] = True
            road_tag = "ancient_highway" if "D4" in cell["zone_id"] else "road"
            cell["terrain_type"] = "ruin_road_main" if road_tag == "ancient_highway" else "road"
            if road_tag not in cell["tags"]:
                cell["tags"].append(road_tag)
            cell["content"]["environment_tags"] = cell["tags"]
        return matrix

    async def _save_matrix_bulk(self, world_matrix: dict) -> None:
        payload = [
            {
                "x": cell["x"],
                "y": cell["y"],
                "zone_id": cell["zone_id"],
                "terrain_type": cell["terrain_type"],
                "content": cell["content"],
                "flags": cell["flags"],
                "services": cell.get("services", []),
                "is_active": cell["flags"].get("is_active", False),
            }
            for cell in world_matrix.values()
        ]
        chunk_size = 500
        for i in range(0, len(payload), chunk_size):
            chunk = payload[i : i + chunk_size]
            await self.world_repo.bulk_upsert_nodes(chunk)
            await asyncio.sleep(0.01)

    async def _spawn_content(self, mode: str) -> None:
        hub_x, hub_y = HUB_CENTER["x"], HUB_CENTER["y"]
        await self.zone_orchestrator.generate_chunk(hub_x, hub_y)
        if mode != "test":
            for i in range(-1, 2):
                for j in range(-1, 2):
                    if i == 0 and j == 0:
                        continue
                    cx, cy = hub_x + (j * 5), hub_y + (i * 5)
                    if 0 <= cx < WORLD_WIDTH and 0 <= cy < WORLD_HEIGHT:
                        await self.zone_orchestrator.generate_chunk(cx, cy)


async def seed_world_final(mode: str = "test"):
    if mode != "content_only":
        log.warning("!!! DROPPING DATABASE SCHEMA !!!")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        log.info("Schema recreated.")
    async with async_session_factory() as session:
        generator = WorldGenerator(session)
        await generator.run(mode)


if __name__ == "__main__":
    log.remove()
    log.add(sys.stderr, level="INFO")
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("=== WORLD GENERATOR v3.0 ===")
    choice = input("Select mode (1: TEST, 2: FULL, 3: CONTENT ONLY): ").strip()
    mode = "full" if choice == "2" else "content_only" if choice == "3" else "test"
    asyncio.run(seed_world_final(mode))
