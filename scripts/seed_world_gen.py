import asyncio
import math
import os
import random
import sys
from typing import cast

from loguru import logger as log

from apps.common.database.model_orm.base import Base
from apps.common.database.model_orm.world import WorldRegion, WorldZone
from apps.common.database.repositories.ORM.world_repo import WorldRepoORM
from apps.common.database.session import async_engine, async_session_factory
from apps.game_core.game_service.monster.clan_factory import ClanFactory
from apps.game_core.game_service.world.content_gen_service import ContentGenerationService
from apps.game_core.game_service.world.gen_utils.path_finder import PathFinder
from apps.game_core.game_service.world.zone_orchestrator import ZoneOrchestrator
from apps.game_core.resources.game_data.graf_data_world.start_vilage import STATIC_LOCATIONS
from apps.game_core.resources.game_data.graf_data_world.world_config import (
    ANCHORS,
    BIOME_DEFINITIONS,
    HUB_CENTER,
    REGION_ROWS,
    REGION_SIZE,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    ZONE_SIZE,
    TerrainMeta,
)

# --- Адаптация под структуру проекта ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class WorldGenerator:
    """
    Генератор игрового мира v3.0 (Noise Biomes + Regional POIs).
    """

    def __init__(self, session):
        self.session = session
        self.world_repo = WorldRepoORM(session)
        self.clan_factory = ClanFactory(session)
        self.content_service = ContentGenerationService(self.world_repo)
        self.zone_orchestrator = ZoneOrchestrator(session, self.world_repo, self.content_service)
        self.regional_pois = []  # Список ключевых точек для дорог
        log.debug("WorldGeneratorInit")

    async def run(self, mode: str = "test") -> None:
        log.info(f"WorldGen | event=start mode={mode}")

        if mode != "content_only":
            # 1. Структура (Регионы и Зоны)
            log.info("WorldGen | step=1_create_structure")
            await self._create_regions_and_zones()

            # 2. Матрица в памяти
            log.info("WorldGen | step=2_generate_matrix_ram")
            world_matrix = self._generate_world_matrix()

            # 3. Скелет мира (Стены, Оплоты, Дороги)
            world_matrix = self._build_world_skeleton(world_matrix)

            # 4. Сохранение (BULK)
            log.info(f"WorldGen | step=3_bulk_save items={len(world_matrix)}")
            await self._save_matrix_bulk(world_matrix)

            await self.session.commit()
            log.info("WorldGen | event=structure_committed")

        # 5. Контент (LLM)
        log.info("WorldGen | step=4_spawn_content")
        await self._spawn_content(mode)
        await self.session.commit()
        log.info("WorldGen | event=complete")

    async def _create_regions_and_zones(self) -> None:
        """Создает регионы и зоны. D4 — особый случай."""
        for row_char in REGION_ROWS:
            for col_idx in range(1, 8):
                reg_id = f"{row_char}{col_idx}"
                await self.world_repo.upsert_region(WorldRegion(id=reg_id, climate_tags=[]))

                for zx in range(3):
                    for zy in range(3):
                        zone_id = f"{reg_id}_{zx}_{zy}"
                        reg_row_idx = REGION_ROWS.index(row_char)

                        # Абсолютные координаты центра зоны
                        center_x = (col_idx - 1) * REGION_SIZE + zx * ZONE_SIZE + ZONE_SIZE // 2
                        center_y = reg_row_idx * REGION_SIZE + zy * ZONE_SIZE + ZONE_SIZE // 2

                        flags = {}

                        # --- ЛОГИКА D4 (Цитадель) ---
                        if reg_id == "D4":
                            if zx == 1 and zy == 1:
                                # ЦЕНТР ХАБА
                                biome_id = "hub_district"
                                tier = 0
                                # 🔥 ГЛАВНОЕ: Ставим флаг безопасности явно
                                flags = {"is_safe_zone": True, "is_passable": True}
                            else:
                                # ОКРАИНЫ (Руины)
                                biome_id = "city_ruins"
                                tier = 0  # <--- БЫЛО 1, СТАВЬ 0
                                flags = {"is_safe_zone": False, "is_passable": True}
                        else:
                            # --- ВНЕШНИЙ МИР (Шум) ---
                            biome_id = self._get_biome_noise(center_x, center_y)

                            # Тир зависит от дальности от Хаба
                            dist = math.sqrt((center_x - 52) ** 2 + (center_y - 52) ** 2)
                            tier = min(7, int(dist / 15) + 1)

                        await self.world_repo.upsert_zone(
                            WorldZone(id=zone_id, region_id=reg_id, biome_id=biome_id, tier=tier, flags=flags)
                        )
        await self.session.flush()

    def _get_biome_noise(self, x: int, y: int) -> str:
        """
        Генерирует "пятна" биомов с помощью синусоидного шума.
        Никакой привязки к Якорям. Чистый хаос.
        """
        natural_biomes = ["forest", "swamp", "mountains", "wasteland", "canyon", "jungle", "badlands", "grassland"]

        # Масштаб шума (меньше = крупнее пятна)
        scale = 0.12
        # Сдвиг, чтобы не было зеркальности
        val = math.sin(x * scale) + math.cos(y * scale * 0.8) + math.sin((x + y) * 0.05)

        # Нормализация (-3..3 -> 0..1)
        normalized = (val + 3) / 6
        idx = int(normalized * len(natural_biomes))
        idx = max(0, min(idx, len(natural_biomes) - 1))

        return natural_biomes[idx]

    def _generate_world_matrix(self) -> dict:
        """Базовая заливка террейна с учетом ВЕСОВ (Spawn Weight)."""
        matrix = {}
        for wx in range(WORLD_WIDTH):
            for wy in range(WORLD_HEIGHT):
                # ID Зоны
                col = (wx // REGION_SIZE) + 1
                row_idx = min(wy // REGION_SIZE, len(REGION_ROWS) - 1)
                row_char = REGION_ROWS[row_idx]
                reg_id = f"{row_char}{col}"

                local_x = wx % REGION_SIZE
                local_y = wy % REGION_SIZE
                zone_x = local_x // ZONE_SIZE
                zone_y = local_y // ZONE_SIZE
                zone_id = f"{reg_id}_{zone_x}_{zone_y}"

                # Биом
                biome_id = "city_ruins" if reg_id == "D4" else self._get_biome_noise(wx, wy)

                # --- ИСПРАВЛЕНИЕ: ВЗВЕШЕННЫЙ ВЫБОР ТАЙЛА ---
                biome_config = BIOME_DEFINITIONS.get(biome_id, {})
                t_key = "flat"

                if biome_config:
                    population = []
                    weights = []

                    for key, data in biome_config.items():
                        # Фильтруем только фон
                        if data.get("role") != "background":
                            continue

                        # БЕРЕМ ВЕС ИЗ КОНФИГА
                        w = data.get("spawn_weight", 0)

                        # Если вес > 0, добавляем в рулетку
                        if w > 0:
                            population.append(key)
                            weights.append(w)

                    if population:
                        # random.choices уважает веса (шанс 40 будет падать чаще, чем 10)
                        t_key = random.choices(population, weights=weights, k=1)[0]
                    else:
                        # Если конфиг пустой или везде вес 0 — берем первый попавшийся
                        # (или дефолтный flat, чтобы не крашнулось)
                        t_key = next(iter(biome_config.keys()), "flat")

                # ---------------------------------------------

                terrain_meta: TerrainMeta = cast(TerrainMeta, biome_config.get(t_key, {}))
                env_tags = terrain_meta.get("visual_tags", []) + [biome_id]

                matrix[(wx, wy)] = {
                    "x": wx,
                    "y": wy,
                    "zone_id": zone_id,
                    "terrain_type": t_key,
                    "tags": list(set(env_tags)),
                    "flags": {"is_passable": terrain_meta.get("is_passable", True)},
                    "content": {"title": t_key, "description": "", "environment_tags": list(set(env_tags))},
                    "services": [],
                }
        return matrix

    def _build_world_skeleton(self, matrix: dict) -> dict:
        """
        Главный архитектор: Статика -> Стена -> Оплоты -> Дороги.
        """
        # 1. Статика (Хаб)
        for (wx, wy), static_data in STATIC_LOCATIONS.items():
            if (wx, wy) in matrix:
                cell = matrix[(wx, wy)]
                cell["terrain_type"] = "static_structure"
                cell["flags"].update(static_data["flags"])
                cell["content"] = dict(static_data["content"])
                cell["services"] = static_data.get("services", [])
                if "environment_tags" in cell["content"]:
                    cell["tags"] = cell["content"]["environment_tags"]

        # 2. Стена D4 (Периметр)
        d4_min, d4_max = 45, 59
        gates = []

        for x in range(d4_min, d4_max + 1):
            for y in range(d4_min, d4_max + 1):
                is_border = x in (d4_min, d4_max) or y in (d4_min, d4_max)
                if is_border:
                    mid = (d4_min + d4_max) // 2
                    is_gate = x == mid or y == mid

                    if is_gate:
                        matrix[(x, y)]["terrain_type"] = "city_gate_outer"
                        matrix[(x, y)]["tags"].append("gate")
                        matrix[(x, y)]["flags"]["is_passable"] = True
                        gates.append((x, y))
                    else:
                        matrix[(x, y)]["terrain_type"] = "monolithic_wall"
                        matrix[(x, y)]["tags"].append("wall")
                        matrix[(x, y)]["flags"]["is_passable"] = False

        # 3. Региональные Оплоты (POI)
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

        # 4. Дороги (Лабиринт)
        matrix = self._generate_roads_graph(matrix, gates)

        return matrix

    def _calculate_costs_for_pathfinding(self, matrix: dict) -> None:
        """
        [DATA-DRIVEN]
        Пробегает по всей матрице и проставляет flags['travel_cost'] на основе КОНФИГА (BIOME_DEFINITIONS).
        """
        terrain_props_cache = {}

        for _biome_key, terrains in BIOME_DEFINITIONS.items():
            for t_key, t_data in terrains.items():
                terrain_props_cache[t_key] = {
                    "cost": t_data.get("travel_cost", 1.0),
                    "is_passable": t_data.get("is_passable", True),
                }

        terrain_props_cache["static_structure"] = {"cost": 999.0, "is_passable": False}

        for cell in matrix.values():
            t_type = cell["terrain_type"]
            flags = cell["flags"]

            props = terrain_props_cache.get(t_type)

            if props:
                base_cost = props["cost"]
                conf_passable = props["is_passable"]
            else:
                base_cost = 1.0
                conf_passable = True

            if not conf_passable or not flags.get("is_passable", True) or base_cost <= 0.01:
                final_cost = 999.0
            else:
                final_cost = base_cost

            if "road" in cell["tags"]:
                final_cost = min(final_cost, 0.5)

            cell["flags"]["travel_cost"] = final_cost

    def _generate_roads_graph(self, matrix: dict, gates: list) -> dict:
        """
        Строит дороги, используя матрицу с расчитанными ценами.
        """
        log.info("PathFinder | Pre-calculating travel costs...")

        self._calculate_costs_for_pathfinding(matrix)

        path_finder = PathFinder(matrix)

        road_cells = set()

        poi_grid = {}
        for px, py in self.regional_pois:
            col_idx = px // REGION_SIZE
            row_idx = py // REGION_SIZE
            poi_grid[(row_idx, col_idx)] = (px, py)

        hub_idx = (3, 3)
        connected_pairs = set()

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

        for r in range(7):
            for c in range(7):
                if (r, c) == hub_idx:
                    continue
                if (r, c) not in poi_grid:
                    continue

                current_poi = poi_grid[(r, c)]

                neighbors = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
                neighbors.sort(key=lambda n: abs(n[0] - 3) + abs(n[1] - 3))

                connected_to_hubward = False

                for nr, nc in neighbors:
                    if (nr, nc) == hub_idx:
                        continue
                    if not (0 <= nr < 7 and 0 <= nc < 7):
                        continue

                    neighbor_poi = poi_grid.get((nr, nc))
                    if not neighbor_poi:
                        continue

                    pair_id = tuple(sorted(((r, c), (nr, nc))))

                    is_closer_to_hub = (abs(nr - 3) + abs(nc - 3)) < (abs(r - 3) + abs(c - 3))
                    should_connect = False

                    if is_closer_to_hub and not connected_to_hubward:
                        should_connect = True
                        connected_to_hubward = True
                    elif pair_id not in connected_pairs and random.random() < 0.15:
                        should_connect = True

                    if should_connect:
                        path = path_finder.get_path(current_poi, neighbor_poi)
                        if path:
                            road_cells.update(path)
                            connected_pairs.add(pair_id)

        anchor_points = [(a["x"], a["y"]) for a in ANCHORS]
        for anchor in anchor_points:
            if not self.regional_pois:
                continue
            closest_poi = min(self.regional_pois, key=lambda p: abs(p[0] - anchor[0]) + abs(p[1] - anchor[1]))
            path = path_finder.get_path(closest_poi, anchor)
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

            road_tag = "dirt_path"
            if "D4" in cell["zone_id"]:
                road_tag = "ancient_highway"
                cell["terrain_type"] = "ruin_road_main"
            else:
                road_tag = "road"
                cell["terrain_type"] = "road"

            if road_tag not in cell["tags"]:
                cell["tags"].append(road_tag)

            cell["content"]["environment_tags"] = cell["tags"]

        return matrix

    async def _save_matrix_bulk(self, world_matrix: dict) -> None:
        payload = []
        for cell in world_matrix.values():
            clean_node = {
                "x": cell["x"],
                "y": cell["y"],
                "zone_id": cell["zone_id"],
                "terrain_type": cell["terrain_type"],
                "content": cell["content"],
                "flags": cell["flags"],
                "services": cell.get("services", []),
                "is_active": cell["flags"].get("is_active", False),
            }
            payload.append(clean_node)

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
                    cx = hub_x + (j * 5)
                    cy = hub_y + (i * 5)
                    if 0 <= cx < WORLD_WIDTH and 0 <= cy < WORLD_HEIGHT:
                        log.info(f"ContentSpawn | Neighbors Chunk ({cx}, {cy})")
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

    print("=== WORLD GENERATOR v3.0 (Noise + POI + Walls) ===")
    print("1. TEST Mode (Hub + Walls)")
    print("2. FULL Mode (Hub + Neighbors)")
    print("3. CONTENT ONLY")

    choice = input("Select mode: ").strip()
    mode = "full" if choice == "2" else "content_only" if choice == "3" else "test"

    asyncio.run(seed_world_final(mode))
